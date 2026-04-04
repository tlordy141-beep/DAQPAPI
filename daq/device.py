"""
device.py — DT9805 device handle and low-level voltage reading.

Wraps the DT-Open Layers Win32 SDK (oldaapi64.dll) via Python ctypes.

Usage:
    with DT9805Device() as dev:
        volts = dev.read_voltage(channel=1, gain=100)

The context manager keeps the board handle open for the duration of the
`with` block, so you can read many channels without re-opening the board
each time.
"""
import ctypes
import ctypes.wintypes as wt
import sys

# ---------------------------------------------------------------------------
# Load DLL
# ---------------------------------------------------------------------------
try:
    _olda = ctypes.WinDLL("oldaapi64.dll")
except OSError as exc:
    sys.exit(
        f"Cannot load oldaapi64.dll: {exc}\n"
        "Ensure the DT-Open Layers driver is installed and the DT9805 is connected."
    )

# ---------------------------------------------------------------------------
# Constants  (OLDADEFS.H)
# ---------------------------------------------------------------------------
OLSS_AD           = 0    # Subsystem type: Analog-to-Digital
OL_DF_SINGLEVALUE = 801  # Data-flow mode: polled single-value read
OL_ENC_BINARY     = 200  # Encoding: unsigned offset binary
OLNOERROR         = 0    # Return code for success

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check(ecode: int, where: str = "") -> None:
    """Raise RuntimeError if ecode is not OLNOERROR."""
    if ecode != OLNOERROR:
        buf = ctypes.create_string_buffer(256)
        _olda.olDaGetErrorString(ecode, buf, 256)
        desc = buf.value.decode("ascii", errors="replace") or f"code {ecode}"
        raise RuntimeError(f"DT error{' @ ' + where if where else ''}: {desc}")


# Board-enumeration callback.
# Signature: BOOL CALLBACK (PTSTR pszBrdName, PTSTR pszEntry, LPARAM lParam)
# oldaapi64.dll uses ANSI (single-byte) strings → c_char_p, not c_wchar_p.
_BoardCB = ctypes.WINFUNCTYPE(
    wt.BOOL,
    ctypes.c_char_p,   # pszBrdName
    ctypes.c_char_p,   # pszEntry
    ctypes.c_void_p,   # lParam
)

# ---------------------------------------------------------------------------
# DT9805Device
# ---------------------------------------------------------------------------

class DT9805Device:
    """
    Manages the connection to the DT9805 DAQ.

    Open/close via context manager:
        with DT9805Device() as dev:
            v = dev.read_voltage(channel=1, gain=100)

    Or manually:
        dev = DT9805Device()
        dev.open()
        ...
        dev.close()
    """

    def __init__(self):
        self._hdev  = ctypes.c_void_p(None)   # device handle
        self._hdass = ctypes.c_void_p(None)   # A/D subsystem handle
        self._board_name = ""
        self._is_open = False

    # ------------------------------------------------------------------ open

    def open(self) -> None:
        """Find the first available DT-Open Layers board and open it."""
        if self._is_open:
            return

        # Use a local flag variable captured by the callback closure
        found_hdev = ctypes.c_void_p(None)
        found_name = [b""]

        @_BoardCB
        def _grab_first(pszName, pszEntry, lParam):
            h = ctypes.c_void_p(None)
            _olda.olDaInitialize(pszName, ctypes.byref(h))
            if h.value is not None:
                found_hdev.value = h.value
                found_name[0]    = pszName or b""
                return False   # stop enumeration
            return True        # keep looking

        _check(_olda.olDaEnumBoards(_grab_first, None), "EnumBoards")

        if found_hdev.value is None:
            raise RuntimeError("No DT-Open Layers board found — is the DT9805 plugged in?")

        self._hdev.value  = found_hdev.value
        self._board_name  = found_name[0].decode("ascii", errors="replace")

        # Get the A/D subsystem handle (element 0 = the only AD subsystem)
        _check(
            _olda.olDaGetDASS(self._hdev, OLSS_AD, 0, ctypes.byref(self._hdass)),
            "GetDASS"
        )

        # Configure for single polled reads — committed once, used for all reads
        _check(_olda.olDaSetDataFlow(self._hdass, OL_DF_SINGLEVALUE), "SetDataFlow")
        _check(_olda.olDaConfig(self._hdass), "Config")

        self._is_open = True
        print(f"[DT9805] Opened: {self._board_name}")

    # ----------------------------------------------------------------- close

    def close(self) -> None:
        """Release the A/D subsystem and close the board."""
        if not self._is_open:
            return
        _olda.olDaReleaseDASS(self._hdass)
        _olda.olDaTerminate(self._hdev)
        self._hdev.value  = None
        self._hdass.value = None
        self._is_open = False
        print("[DT9805] Closed.")

    # -------------------------------------------- context manager support

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False   # do not suppress exceptions

    # ------------------------------------------------------- voltage read

    def read_voltage(self, channel: int, gain: float = 1.0) -> float:
        """
        Read one voltage sample from a single channel.

        Parameters
        ----------
        channel : int
            Hardware channel index (0 = CJC, 1 = AI1/TC1, ..., 7 = AI7/PT4).
        gain : float
            Gain setting: 1, 10, 100, or 500.
            The gain determines the input voltage range:
                gain=1   → ±10 V    gain=10  → ±1 V
                gain=100 → ±0.1 V   gain=500 → ±0.02 V

        Returns
        -------
        float : measured voltage in volts.

        Raises
        ------
        RuntimeError if the device is not open or the read fails.
        """
        if not self._is_open:
            raise RuntimeError("Device is not open. Call open() or use as a context manager.")

        # Read raw ADC count
        raw_count = ctypes.c_long(0)
        _check(
            _olda.olDaGetSingleValue(
                self._hdass,
                ctypes.byref(raw_count),
                ctypes.c_uint(channel),
                ctypes.c_double(gain),
            ),
            f"GetSingleValue(ch={channel})"
        )

        # Get board parameters needed for count → volts conversion.
        # These are constant for a given gain setting, so re-fetching each call
        # is slightly wasteful but keeps the code simple and correct.
        v_max      = ctypes.c_double(0.0)
        v_min      = ctypes.c_double(0.0)
        encoding   = ctypes.c_uint(0)
        resolution = ctypes.c_uint(0)

        _check(_olda.olDaGetRange(self._hdass, ctypes.byref(v_max), ctypes.byref(v_min)), "GetRange")
        _check(_olda.olDaGetEncoding(self._hdass, ctypes.byref(encoding)), "GetEncoding")
        _check(_olda.olDaGetResolution(self._hdass, ctypes.byref(resolution)), "GetResolution")

        # Count → volts conversion.
        # If encoding is 2's complement, convert to offset binary first
        # by flipping the sign bit (MSB). Offset binary maps 0 → v_min,
        # 2^N - 1 → v_max linearly.
        count = raw_count.value
        bits  = resolution.value

        if encoding.value != OL_ENC_BINARY:
            count ^= (1 << (bits - 1))   # flip MSB: 2's comp → offset binary
            count &= (1 << bits) - 1     # mask to N bits

        # olDaGetRange always returns the ADC's physical range (e.g. ±10 V),
        # regardless of gain. The gain amplifies the input signal before the ADC,
        # so the ADC count represents (actual_input × gain). Dividing by gain
        # converts from ADC-scale back to actual input voltage.
        # e.g. gain=100, ADC range ±10 V → effective input range ±0.1 V
        adc_voltage = (v_max.value - v_min.value) / (1 << bits) * count + v_min.value
        return adc_voltage / gain

    # --------------------------------------------------------- properties

    @property
    def board_name(self) -> str:
        return self._board_name

    @property
    def is_open(self) -> bool:
        return self._is_open

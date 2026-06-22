#pragma once

#ifdef DLP4710EVM_EXPORTS
#define DLP4710EVM_API __declspec(dllexport)
#else
#define DLP4710EVM_API __declspec(dllimport)
#endif


#ifdef __cplusplus
#define CppCALLCONVEN extern "C"
#else
#define CppCALLCONVEN
#endif

/* Export Stuffs */
#ifdef WIN32
#ifdef CYUSBSERIAL_EXPORTS
#define CYWINEXPORT  CppCALLCONVEN __declspec(dllexport)
#define WINCALLCONVEN
#define LINUXCALLCONVEN
#else
#define CYWINEXPORT CppCALLCONVEN __declspec(dllimport)
#define WINCALLCONVEN
#define LINUXCALLCONVEN
#endif
#else /* Linux and MAC */
#define CYWINEXPORT CppCALLCONVEN
#define WINCALLCONVEN
#define LINUXCALLCONVEN
#ifndef BOOL
typedef bool BOOL;
#endif
#endif

#ifndef UINT32
typedef unsigned int UINT32;
#endif
#ifndef UINT8
typedef unsigned char UINT8;
#endif
#ifndef UINT16
typedef unsigned short UINT16;
#endif
#ifndef CHAR
typedef char CHAR;
#endif
#ifndef UCHAR
typedef unsigned char UCHAR;
#endif




#ifndef CY_STRUCT_DEFS_
#define CY_STRING_DESCRIPTOR_SIZE 256                   /**< String descriptor size */
#define CY_MAX_DEVICE_INTERFACE 5                       /**< Maximum number of interfaces */

/**
 *  \brief CyUSB Device Handle.
 *
 *  The handle is used by application to communicate with USB serial device.
 *  The handle is obtained by calling CyOpen.
 *
 *  \sa CyOpen
 */
typedef void* CY_HANDLE;

/**
 *  \brief Function pointer for getting async error/success notification on UART/SPI
 *
 *  This function pointer that will be passed to CySetEventNotification and get
 *  a callback with a 2 byte value bit map that reports error/events triggered during UART/SPI transaction.
 *  The bit map is defined in CY_CALLBACK_EVENTS.
 *
 *  \sa CY_CALLBACK_EVENTS
 */
typedef void (*CY_EVENT_NOTIFICATION_CB_FN)(UINT16 eventsNotified);

/**
 *  \brief This structure is used to hold VID and PID of USB device
 *
 *  This Strucuture holds the VID and PID of a USB device.
 *
 *  \sa CY_DEVICE_INFO
 *  \sa CyGetDeviceInfoVidPid
 */
typedef struct _CY_VID_PID {

    UINT16 vid;         /**< Holds the VID of the device */
    UINT16 pid;         /**< Holds the PID of the device */

} CY_VID_PID, * PCY_VID_PID;

/**
 *  \brief This structure is used to hold version information of the library.
 *
 *  This structure can be used to retrive the version information of the library.
 *
 *  \sa CyGetLibraryVersion
 */
typedef struct _CY_LIBRARY_VERSION {

    UINT8 majorVersion;     /**< The major version of the library */
    UINT8 minorVersion;     /**< The minor version of the library */
    UINT16 patch;           /**< The patch number of the library */
    UINT8 buildNumber;      /**< The build number of the library */

} CY_LIBRARY_VERSION, * PCY_LIBRARY_VERSION;

/**
 *  \brief This structure is used to hold firmware version of the USB Serial device.
 *
 *  This structure holds the version information of the USB serial device.
 *  It has major version, minor version, patch number and build number.
 *
 *  \sa CyGetFirmwareVersion
 */
typedef struct _CY_FIRMWARE_VERSION {

    UINT8 majorVersion;                 /**< Major version of the Firmware */
    UINT8 minorVersion;                 /**< Minor version of the Firmware */
    UINT16 patchNumber;                 /**< Patch Number of the Firmware */
    UINT32 buildNumber;                 /**< Build Number of the Firmware */

} CY_FIRMWARE_VERSION, * PCY_FIRMWARE_VERSION;

/**
 *  \brief Enumeration defining list of USB device classes supported by USB Serial device.
 *
 *  This is the list of USB device classes supported by USB Serial device.
 *
 *  \sa CY_DEVICE_INFO
 *  \sa CyGetDeviceInfo
 *  \sa CyGetDeviceInfoVidPid
 */
typedef enum _CY_DEVICE_CLASS {

    CY_CLASS_DISABLED = 0,              /**< None or the interface is disabled */
    CY_CLASS_CDC = 0x02,                /**< CDC ACM class */
    CY_CLASS_PHDC = 0x0F,               /**< PHDC class */
    CY_CLASS_VENDOR = 0xFF              /**< VENDOR specific class */

} CY_DEVICE_CLASS;

/**
 *  \brief Enumeration defining list of device types supported by USB Serial device in each interface.
 *
 *  This is the list of device types supported by USB Serial device when the interface type is
 *  configured as CY_CLASS_VENDOR. The interface type can be queried from the device by using CyGetDeviceInfo
 *  and CyGetDeviceInfoVidPid APIs.
 *
 *  The member of CY_DEVICE_INFO structure contains the interface type.
 *
 *  \sa CY_DEVICE_INFO
 *  \sa CyGetDeviceInfo
 *  \sa CyGetDeviceInfoVidPid
 */
typedef enum _CY_DEVICE_TYPE {

    CY_TYPE_DISABLED = 0,               /**< Invalid device type or interface is not CY_CLASS_VENDOR */
    CY_TYPE_UART,                       /**< Interface of device is of type UART */
    CY_TYPE_SPI,                        /**< Interface of device is of type SPI */
    CY_TYPE_I2C,                        /**< Interface of device is of type I2C */
    CY_TYPE_JTAG,                       /**< Interface of device is of type JTAG */
    CY_TYPE_MFG                         /**< Interface of device is in Manufacturing mode */

} CY_DEVICE_TYPE;

/**
 *  \brief This enumeration type defines the available device serial blocks.
 *
 *  USB Serial device has up to two configurable serial blocks. UART, SPI, I2C or JTAG functionality can be
 *  configured and used in these serial block. Windows driver binds to a serial block rather than the entire device.
 *  So, it is essential to find out which serial block to which current communications are directed. These enumeration
 *  structure provides the possible SERIAL BLOCK Options.
 *
 *  This enumration data type is a member of CY_DEVICE_INFO structure.
 *
 *  This data type information doesn't apply for non-windows operating system.
 *
 *  \sa CY_DEVICE_INFO
 *  \sa CyGetDeviceInfo
 *  \sa CyGetDeviceInfoVidPid
 */

typedef enum _CY_DEVICE_SERIAL_BLOCK
{
    SerialBlock_SCB0 = 0,               /**< Serial Block Number 0 */
    SerialBlock_SCB1,                   /**< Serial Block Number 1 */
    SerialBlock_MFG                     /**< Serial Block Manufacturing Interface. */

} CY_DEVICE_SERIAL_BLOCK;

/**
 *  \brief Structure to hold information of the device connected to host.
 *
 *  The structure holds the information about device currently connected to host. The information
 *  can be obtained by using CyGetDeviceInfo and CyGetDeviceInfoVidPid APIs.
 *
 *  The information includes VID, PID, number of interfaces, string descriptors, device type
 *  and device class supported by each interface. Device type is valid only if the interface is CY_CLASS_VENDOR.
 *
 *  \sa CY_VID_PID
 *  \sa CY_DEVICE_CLASS
 *  \sa CY_DEVICE_TYPE
 *  \sa CyGetDeviceInfo
 *  \sa CyGetDeviceInfoVidPid
 */
typedef struct _CY_DEVICE_INFO {

    CY_VID_PID vidPid;                                      /**< VID and PID */
    UCHAR numInterfaces;                                    /**< Number of interfaces supported */
    UCHAR manufacturerName[CY_STRING_DESCRIPTOR_SIZE];     /**< Manufacturer name */
    UCHAR productName[CY_STRING_DESCRIPTOR_SIZE];          /**< Product name */
    UCHAR serialNum[CY_STRING_DESCRIPTOR_SIZE];            /**< Serial number */
    UCHAR deviceFriendlyName[CY_STRING_DESCRIPTOR_SIZE];   /**< Device friendly name : Windows only */
    CY_DEVICE_TYPE deviceType[CY_MAX_DEVICE_INTERFACE];    /**< Type of the device each interface has(Valid only
                                                                 for USB Serial Device) and interface in vendor class */
    CY_DEVICE_CLASS deviceClass[CY_MAX_DEVICE_INTERFACE];  /**< Interface class of each interface */

#ifdef WIN32
    CY_DEVICE_SERIAL_BLOCK  deviceBlock; /**< On Windows, each USB Serial device interface is associated with a
                                          *   separate driver instance. This variable represents the present driver
                                          *   interface instance that is associated with a serial block.
                                          */
#endif

} CY_DEVICE_INFO, * PCY_DEVICE_INFO;

/**
 *  \brief This structure is used to hold data buffer information.
 *
 *  This strucuture is used by all the data transaction APIs in the library to perform read, write
 *  operations.
 *  Before using a variable of this strucutre users need to initialize various members appropriately.
 *
 *  \sa CyUartRead
 *  \sa CyUartWrite
 *  \sa CyI2cRead
 *  \sa CyI2cWrite
 *  \sa CySpiReadWrite
 *  \sa CyJtagWrite
 *  \sa CyJtagRead
 */
typedef struct _CY_DATA_BUFFER {

    UCHAR* buffer;                      /**< Pointer to the buffer from where the data is read/written */
    UINT32 length;                      /**< Length of the buffer */
    UINT32 transferCount;               /**< Number of bytes actually read/written */

} CY_DATA_BUFFER, * PCY_DATA_BUFFER;

/**
 *  \brief Enumeration defining return status of  USB serial library APIs
 *
 *  The enumeration CY_RETURN_STATUS holds the different return status of all the
 *  APIs supported by USB Serial library.
 */
typedef enum _CY_RETURN_STATUS {

    CY_SUCCESS = 0,                         /**< API returned successfully without any errors. */
    CY_ERROR_ACCESS_DENIED,                 /**< Access of the API is denied for the application */
    CY_ERROR_DRIVER_INIT_FAILED,            /**< Driver initialisation failed */
    CY_ERROR_DEVICE_INFO_FETCH_FAILED,      /**< Device information fetch failed */
    CY_ERROR_DRIVER_OPEN_FAILED,            /**< Failed to open a device in the library */
    CY_ERROR_INVALID_PARAMETER,             /**< One or more parameters sent to the API was invalid */
    CY_ERROR_REQUEST_FAILED,                /**< Request sent to USB Serial device failed */
    CY_ERROR_DOWNLOAD_FAILED,               /**< Firmware download to the device failed */
    CY_ERROR_FIRMWARE_INVALID_SIGNATURE,    /**< Invalid Firmware signature in firmware file */
    CY_ERROR_INVALID_FIRMWARE,              /**< Invalid firmware */
    CY_ERROR_DEVICE_NOT_FOUND,              /**< Device disconnected */
    CY_ERROR_IO_TIMEOUT,                    /**< Timed out while processing a user request */
    CY_ERROR_PIPE_HALTED,                   /**< Pipe halted while trying to transfer data */
    CY_ERROR_BUFFER_OVERFLOW,               /**< OverFlow of buffer while trying to read/write data */
    CY_ERROR_INVALID_HANDLE,                /**< Device handle is invalid */
    CY_ERROR_ALLOCATION_FAILED,             /**< Error in Allocation of the resource inside the library */
    CY_ERROR_I2C_DEVICE_BUSY,               /**< I2C device busy */
    CY_ERROR_I2C_NAK_ERROR,                 /**< I2C device NAK */
    CY_ERROR_I2C_ARBITRATION_ERROR,         /**< I2C bus arbitration error */
    CY_ERROR_I2C_BUS_ERROR,                 /**< I2C bus error */
    CY_ERROR_I2C_BUS_BUSY,                  /**< I2C bus is busy */
    CY_ERROR_I2C_STOP_BIT_SET,              /**< I2C master has sent a stop bit during a transaction */
    CY_ERROR_STATUS_MONITOR_EXIST           /**< API Failed because the SPI/UART status monitor thread already exists */
} CY_RETURN_STATUS;

/**
 *  \brief This structure is used to store configuration of I2C module.
 *
 *  The structure contains parameters that are used in configuring I2C module of
 *  Cypress USB Serial device. CyGetI2cConfig and CySetI2cConfig APIs can be used to
 *  retrieve and configure I2C module respectively.
 *
 *  \sa CyGetI2cConfig
 *  \sa CySetI2cConfig
 */
typedef struct _CY_I2C_CONFIG {

    UINT32 frequency;               /**< I2C clock frequency 1KHz to 400KHz */
    UINT8 slaveAddress;             /**< Slave address of the I2C module, when it is configured as slave */
    BOOL isMaster;                  /**< true- Master , false- slave */
    BOOL isClockStretch;            /**< true- Stretch clock in case of no data availability
                                         (Valid only for slave mode)
                                         false- Do not Stretch clock */
} CY_I2C_CONFIG, * PCY_I2C_CONFIG;

/**
 *  \brief This structure is used to configure each I2C data transaction.
 *
 *  This structure defines parameters that are used for configuring
 *  I2C module during each data transaction. Which includes setting slave address
 *  (when device is in I2C slave mode), stopbit (to enable or disable) and
 *  Nak bit (to enable or disable).
 *
 *  \sa CyI2cWrite
 *  \sa CyI2cRead
 */
typedef struct _CY_I2C_DATA_CONFIG
{
    UCHAR slaveAddress;     /**< Slave address the master will communicate with */
    BOOL isStopBit;         /**< Set when stop bit is used */
    BOOL isNakBit;          /**< Set when I2C master wants to NAK the slave after read
                                 Applicable only when doing I2C read */
} CY_I2C_DATA_CONFIG, * PCY_I2C_DATA_CONFIG;

/**
 *  \brief Enumeration defining SPI protocol types supported by USB Serial SPI module.
 *
 *  These are the different protocols supported by USB-Serial SPI module.
 *
 *  \sa CY_SPI_CONFIG
 *  \sa CyGetSpiConfig
 *  \sa CySetSpiConfig
 */
typedef enum _CY_SPI_PROTOCOL {

    CY_SPI_MOTOROLA = 0,  /**< In master mode, when not transmitting data (SELECT is inactive), SCLK is stable at CPOL.
                           *   In slave mode, when not selected, SCLK is ignored; i.e. it can be either stable or clocking.
                           *   In master mode, when there is no data to transmit (TX FIFO is empty), SELECT is inactive.
                           */
    CY_SPI_TI,            /**< In master mode, when not transmitting data, SCLK is stable at '0'.
                           *   In slave mode, when not selected, SCLK is ignored - i.e. it can be either stable or clocking.
                           *   In master mode, when there is no data to transmit (TX FIFO is empty), SELECT is inactive -
                           *   i.e. no pulse is generated.
                           *   *** It supports only mode 1 whose polarity values are
                           *   CPOL = 0
                           *   CPHA = 1
                           */
    CY_SPI_NS             /**< In master mode, when not transmitting data, SCLK is stable at '0'. In slave mode,
                           *   when not selected, SCLK is ignored; i.e. it can be either stable or clocking.
                           *   In master mode, when there is no data to transmit (TX FIFO is empty), SELECT is inactive.
                           *   *** It supports only mode 0 whose polarity values are
                           *   CPOL = 0
                           *   CPHA = 0
                           */
} CY_SPI_PROTOCOL;

/**
 *  \brief This structure is used to configure the SPI module of USB Serial device.
 *
 *  This structure defines configuration parameters that are used for configuring the SPI module .
 *
 *  \sa CY_SPI_PROTOCOL
 *  \sa CY_SPI_DATA_TRANSFER_MODE
 *  \sa CyGetSpiConfig
 *  \sa CySetSpiConfig
 */
typedef struct _CY_SPI_CONFIG
{

    UINT32 frequency;                               /**< SPI clock frequency.
                                                     *   ** IMPORTANT: The frequency range supported by SPI module is
                                                     *   1000(1KHz) to 3000000(3MHz)
                                                     */

    UCHAR dataWidth;                                /**< Data width in bits. The valid values are from 4 to 16. */

    CY_SPI_PROTOCOL protocol;                      /**< SPI Protocols to be used as defined in CY_SPI_PROTOCOL */

    BOOL isMsbFirst;                                /**< false -> least significant bit is sent out first
                                                         true -> most significant bit is sent out first */

    BOOL isMaster;                                  /**< false --> Slave mode selected:
                                                         true --> Master mode selected*/

    BOOL isContinuousMode;                          /**< true - Slave select line is not asserted i.e
                                                     *   de-asserted for every word.
                                                     *   false- Slave select line is always asserted
                                                     */

    BOOL isSelectPrecede;                           /**< Valid only in TI mode.
                                                     *   true - The start pulse precedes the first data
                                                     *   false - The start pulse is in sync with first data.
                                                     */

    BOOL isCpha;                                    /**< false - Clock phase is 0; true - Clock phase is 1. */

    BOOL isCpol;                                    /**< false - Clock polarity is 0;true - Clock polarity is 1. */

}CY_SPI_CONFIG, * PCY_SPI_CONFIG;

/**
 *  \brief Enumeration defines UART baud rates supported by UART module of USB Serial device.
 *
 *  The enumeration lists the various baud rates supported by the UART when it is in UART
 *  vendor mode.
 *
 *  \sa CY_UART_CONFIG
 *  \sa CySetUartConfig
 *  \sa CyGetUartConfig
 */
typedef enum _CY_UART_BAUD_RATE
{
    CY_UART_BAUD_300 = 300,          /**< Baud rate of 300. */
    CY_UART_BAUD_600 = 600,          /**< Baud rate of 600. */
    CY_UART_BAUD_1200 = 1200,        /**< Baud rate of 1200. */
    CY_UART_BAUD_2400 = 2400,        /**< Baud rate of 2400. */
    CY_UART_BAUD_4800 = 4800,        /**< Baud rate of 4800. */
    CY_UART_BAUD_9600 = 9600,        /**< Baud rate of 9600. */
    CY_UART_BAUD_14400 = 14400,      /**< Baud rate of 14400. */
    CY_UART_BAUD_19200 = 19200,      /**< Baud rate of 19200. */
    CY_UART_BAUD_38400 = 38400,      /**< Baud rate of 38400. */
    CY_UART_BAUD_56000 = 56000,      /**< Baud rate of 56000. */
    CY_UART_BAUD_57600 = 57600,      /**< Baud rate of 57600. */
    CY_UART_BAUD_115200 = 115200,    /**< Baud rate of 115200. */
    CY_UART_BAUD_230400 = 230400,    /**< Baud rate of 230400. */
    CY_UART_BAUD_460800 = 460800,    /**< Baud rate of 460800. */
    CY_UART_BAUD_921600 = 921600,    /**< Baud rate of 921600. */
    CY_UART_BAUD_1000000 = 1000000,  /**< Baud rate of 1000000. */
    CY_UART_BAUD_3000000 = 3000000,  /**< Baud rate of 3000000. */

}CY_UART_BAUD_RATE;

/**
 *  \brief Enumeration defines the different parity modes supported by UART module of USB Serial device.
 *
 *  This enumeration defines the different parity modes of USB Serial UART module.
 *  It supports odd, even, mark and space parity modes.
 *
 *  \sa CY_UART_CONFIG
 *  \sa CySetUartConfig
 *  \sa CyGetUartConfig
 */
typedef enum _CY_UART_PARITY_MODE {

    CY_DATA_PARITY_DISABLE = 0,         /**< Data parity disabled */
    CY_DATA_PARITY_ODD,                 /**< Odd Parity */
    CY_DATA_PARITY_EVEN,                /**< Even Parity */
    CY_DATA_PARITY_MARK,                /**< Mark parity */
    CY_DATA_PARITY_SPACE                /**< Space parity */

} CY_UART_PARITY_MODE;

/**
 *  \brief Enumeration defines the different stop bit values supported by UART module of USB Serial device.
 *
 *  \sa CY_UART_CONFIG
 *  \sa CySetUartConfig
 *  \sa CyGetUartConfig
 */
typedef enum _CY_UART_STOP_BIT {

    CY_UART_ONE_STOP_BIT = 1,       /**< One stop bit */
    CY_UART_TWO_STOP_BIT            /**< Two stop bits */

} CY_UART_STOP_BIT;

/**
 *  \brief Enumeration defines flow control modes supported by UART module of USB Serial device.
 *
 *  The list provides the various flow control modes supported by USB Serial device.
 *
 *  \sa CyUartSetHwFlowControl
 *  \sa CyUartGetHwFlowControl
 */
typedef enum _CY_FLOW_CONTROL_MODES {

    CY_UART_FLOW_CONTROL_DISABLE = 0,       /**< Disable Flow control */
    CY_UART_FLOW_CONTROL_DSR,               /**< Enable DSR mode of flow control */
    CY_UART_FLOW_CONTROL_RTS_CTS,           /**< Enable RTS CTS mode of flow control */
    CY_UART_FLOW_CONTROL_ALL                /**< Enable RTS CTS and DSR flow control */

} CY_FLOW_CONTROL_MODES;

/**
 *  \brief Structure holds configuration of UART module of USB Serial device.
 *
 *  This structure defines parameters used for configuring the UART module.
 *  CySetUartConfig and CyGetUartConfig APIs are used to configure and retrieve
 *  the UART configuration information.
 *
 *  \sa CySetUartConfig
 *  \sa CyGetUartConfig
 */
typedef struct _CY_UART_CONFIG {

    CY_UART_BAUD_RATE baudRate;             /**< Baud rate as defined in CY_UART_BAUD_RATE */
    UINT8 dataWidth;                        /**< Data width: valid values 7 or 8 */
    CY_UART_STOP_BIT stopBits;              /**< Number of stop bits to be used 1 or 2 */
    CY_UART_PARITY_MODE parityMode;         /**< UART parity mode as defined in CY_UART_PARITY_MODE */
    BOOL isDropOnRxErrors;                  /**< Whether to ignore framing as well as parity errors and receive data */

} CY_UART_CONFIG, * PCY_UART_CONFIG;

/**
 *  \brief Enumeration defining UART/SPI transfer error or status bit maps.
 *
 *  Enumeration lists the bit maps that are used to report error or status during
 *  UART/SPI transfer.
 *
 *  \sa CySetEventNotification
 */
typedef enum _CY_CALLBACK_EVENTS {

    CY_UART_CTS_BIT = 0x01,                         /**< CTS pin notification bit */
    CY_UART_DSR_BIT = 0x02,                         /**< State of transmission carrier. This signal
                                                         corresponds to V.24 signal 106 and RS-232 signal DSR. */
    CY_UART_BREAK_BIT = 0x04,                       /**< State of break detection mechanism of the device */
    CY_UART_RING_SIGNAL_BIT = 0x08,                /**< State of ring signal detection of the device */
    CY_UART_FRAME_ERROR_BIT = 0x10,                 /**< A framing error has occurred */
    CY_UART_PARITY_ERROR_BIT = 0x20,                /**< A parity error has occured */
    CY_UART_DATA_OVERRUN_BIT = 0x40,                /**< Received data has been discarded due to overrun in
                                                     *   the device
                                                     */
    CY_UART_DCD_BIT = 0x100,                        /**< State of receiver carrier detection mechanism of
                                                     *   device. This signal corresponds to V.24 signal 109
                                                     *   and RS-232 signal DCD
                                                     */
    CY_SPI_TX_UNDERFLOW_BIT = 0x200,                /**< Notification sent when SPI fifo is empty */
    CY_SPI_BUS_ERROR_BIT = 0x400,                  /**< Spi bus error has been detected */
    CY_ERROR_EVENT_FAILED_BIT = 0x800               /**< Event thread failed */

} CY_CALLBACK_EVENTS;

#endif

typedef unsigned char DLP4710EVM_DEVICE_IDENTIFIER;
typedef  char* BYTES;
typedef struct DLP4710EVM {
    CY_HANDLE handle;
    UINT8 dev_id = 0;
    UINT8 channel = 0;
};


typedef enum DLP4710_API_ERROR {
    OK = 0,
    ERROR_USED_HANDLE,
    CY_ERROR,
    ERROR_BUS_ACCESS,
    ERROR_INCOMPLETE_WRITE,
    ERROR_WRITE_FAIL,
    ERROR_INCOMPLETE_READ,
    ERROR_READ_FAIL,
    ERROR_AUTOCONF,
    ERROR_NO_DEVICE,

};


namespace DLP4710 {
    extern "C" DLP4710EVM_API  void Version(int* a, int* b);

    extern "C" DLP4710EVM_API int CSerialDeviceNumber(unsigned char* num);
    extern "C" DLP4710EVM_API char* DeviceInfo(DLP4710EVM_DEVICE_IDENTIFIER id);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR Open(DLP4710EVM_DEVICE_IDENTIFIER id, DLP4710EVM *DLP);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR Close(DLP4710EVM DLP);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR SetI2CBusAccess(DLP4710EVM DLP, BOOL enable);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteCommand(DLP4710EVM DLP, char* command, int length, int* tc);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteReadCommand(DLP4710EVM DLP, char* command, int length, int* tc, int readc, char* read);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR ConfigureAutoconnect(DLP4710EVM_DEVICE_IDENTIFIER id, char* fnameo);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR OpenWithAutoconnect(DLP4710EVM * DLP, char* fnameo);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteOperateMode(DLP4710EVM DLP, UINT8 mode);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR ReadOperateMode(DLP4710EVM DLP, UINT8* mode);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteDisplaySize(DLP4710EVM DLP, UINT16 width, UINT16 height);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR ReadDisplaySize(DLP4710EVM DLP, UINT16* widthp, UINT16* heightp);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteExternalVideoSourceFormat(DLP4710EVM DLP, UINT8 frmt);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR ReadExternalVideoSourceFormat(DLP4710EVM DLP, UINT8 * frmt);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteRGBCurrent(DLP4710EVM DLP, UINT16 r, UINT16 g, UINT16 b);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteRGBCurrentMax(DLP4710EVM DLP, UINT16 r, UINT16 g, UINT16 b);


    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteImageOrient(DLP4710EVM DLP, bool LAflip, bool SAflip);

    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteTriggerIn(DLP4710EVM DLP, bool en, bool polarity);
    extern "C" DLP4710EVM_API DLP4710_API_ERROR WriteTriggerOut(DLP4710EVM DLP, bool select, bool en, bool polarity, bool invert, UINT32 delay);

    extern "C" DLP4710EVM_API int CyOpen_(UINT8 deviceNumber, UINT8 interfaceNum, CY_HANDLE * handle);
};

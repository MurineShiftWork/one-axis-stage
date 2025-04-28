// Dependencies:
//  Dynamixel2Arduino library from ROBOTIS, v0.8.0
#include <Dynamixel2Arduino.h>

#define DEBUG_PRINT 0                                                      // Enable debug print statements
#define OUTPUT_TTL 0                                                       // whether to output TTLs while moving
#define dxl_serial Serial                                                  // Dynamixel communication port
#define cmd Serial2                                                        // Command input port
#define dxl_protocol_version 2.0                                           // Dynamixel protocol version, as float 1.0 or 2.0
#define dxl_dir_pin 2                                                      // Direction control pin
#define dxl_baudrate 115200                                                // Dynamixel baud rate
#define cmd_baudrate 115200                                                // Command input baud rate
#define move_ttl_pin 30                                                    // TTL pin for move indication
#define MAX_ID 253                                                         // Maximum Dynamixel ID to scan
#define MOVE_TIMEOUT 1000                                                  // Timeout duration in milliseconds
#define MOVE_QUERY_INTERVAL 5                                              // Interval to query position in milliseconds
#define TARGET_TOLERANCE 10                                                 // Tolerance in position units
#define MAX_BAUD 5                                                         // Number of baud rates to scan
const int32_t buad[MAX_BAUD] = {57600, 115200, 1000000, 2000000, 3000000}; // Baud rates to scan

Dynamixel2Arduino dxl(dxl_serial, dxl_dir_pin); // Dynamixel object
using namespace ControlTableItem;

void setup()
{
    // Initialize command communication
    cmd.begin(cmd_baudrate);
    while (!cmd)
        ;

    // Initialize Dynamixel communication
    dxl.begin(dxl_baudrate);
    dxl.setPortProtocolVersion(dxl_protocol_version);

    // Initialize move indication pin
    pinMode(move_ttl_pin, OUTPUT);
    digitalWrite(move_ttl_pin, LOW); // Set TTL pin low initially
}

void loop()
{
    static byte startByte = '<';
    static byte stopByte = '>';
    static byte commandChar;
    // static uint16_t int1;
    // static uint16_t int2;

    static bool receiving = false;
    static byte buffer[256];
    static int bufferIndex = 0;

    // Check if data is available
    while (cmd.available())
    {
        byte incomingByte = cmd.read();

        if (incomingByte == startByte)
        {
            // Start receiving message
            receiving = true;
            bufferIndex = 0;
            continue;
        }

        // EVAL: Stop receiving message and process data
        if (incomingByte == stopByte)
        {
            receiving = false;
            commandChar = buffer[0];

            switch (commandChar)
            // Command API
            // SET
            //
            //  move one                     device id (int)       position raw (int)   -> None
            //  move multiple                [(id, pos), (id, pos), ...]                -> None
            //
            //  new baudrate                 device id (int)        baudrate (int)      -> success (bool)
            //  new id                       device id (int)        new id (int)        -> success (bool)
            //  flash                        device id (int)        other specs for flash  -> None
            //  set velocity                 device id (int)        new velocity (int)      -> success (bool)
            //  set operating mode           device id (int)        mode (str)          -> success (bool)
            //
            // GET
            //
            //  get info one                 device id              -> str: dict of info
            //  get info all                 list of IDs            -> str: list of dicts for info on each device
            //  scan all                                            -> str: list of dicts for info on each device
            {
            // GETTERS
            case 's': // Scan for devices
                if (DEBUG_PRINT)
                    Serial.println("about to scan for devices...");

                scanForDevices();
                break;

            case 'i':
                // Get info one
                // Expecting at least one cmd char + one integer (2 bytes)
                if (bufferIndex >= 3)
                {
                    uint16_t id = (buffer[1] << 8) | buffer[2]; // Combine two bytes to form integer
                    String info = getInfoById(id);
                    cmd.println(info);
                }
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'i'");
                }
                break;

//             case 'I':
//                 // Get info all
//                 // for each id (input needs to be array), call get info one and append string
//                 // solve like move-multiple: for each int in buffer, call getInfoById, then return list
//
//                 if (bufferIndex >= 3)
//                 {
//                     String info = "[";
//
//                     // for each device id
//                     for (int i = 1; i < bufferIndex; i += 2)
//                     {
//                         uint16_t id = (buffer[i] << 8) | buffer[i + 1];           // Combine two bytes to form integer
//                         info += getInfoById(id);
//                         info += ",";
//
//                     }//end: IDs
//
//                     info += "]";
//
//                     cmd.println(info);
//
//                 }//end: I
//                 else
//                 {
//                     if (DEBUG_PRINT)
//                         Serial.println("Invalid command length for 'I'");
//                 }
//                 break;

            case 'p':
                // Get position
                // Expecting at least one cmd char + one integer (2 bytes)
                if (bufferIndex >= 3)
                {
                    uint16_t id = (buffer[1] << 8) | buffer[2]; // Combine two bytes to form integer
                    getPosition(id);
                }
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'p'");
                }
                break;

            // SETTERS
            case 'm':                 // Move device
                if (bufferIndex >= 5) // Expecting at least one character + two integers (2 bytes each) -> 5 bytes
                {
                    // Unpack the message
                    // commandChar = buffer[0];
                    uint16_t id = (buffer[1] << 8) | buffer[2];       // Combine two bytes to form integer
                    uint16_t position = (buffer[3] << 8) | buffer[4]; // Combine two bytes to form integer

                    setPosition(id, position);

#if OUTPUT_TTL
                    digitalWrite(move_ttl_pin, HIGH);
                        // Wait for the move to complete or timeout
                        unsigned long startTime = millis();
                        while (millis() - startTime < MOVE_TIMEOUT)
                        {
                            int currentPosition = dxl.getPresentPosition(id, UNIT_RAW);

                            if (abs(currentPosition - position) <= TARGET_TOLERANCE)
                            {
                                break; // Target reached within tolerance
                            }
                            delay(MOVE_QUERY_INTERVAL); // Small delay to avoid busy waiting
                        }
                        digitalWrite(move_ttl_pin, LOW);
#endif

                }//end: m
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'm'");
                }
                break;
                // todo: other commands:
                // s=scan, k=move multiple, p=get position, i=get info one, a=get info all,
                // f=flash, b=baudrate, i=set id, v=set velocity, o=mode,

            case 'M':
                // Move multiple devices
                // Expecting at least one character + pairs of two integers (2 bytes each)
                if (bufferIndex >= 5 && (bufferIndex - 1) % 4 == 0)
                {
                    // for each tuple of (device id, target position)
                    for (int i = 1; i < bufferIndex; i += 4)
                    {
                        uint16_t id = (buffer[i] << 8) | buffer[i + 1];           // Combine two bytes to form integer
                        uint16_t position = (buffer[i + 2] << 8) | buffer[i + 3]; // Combine two bytes to form integer

                        setPosition(id, position);

#if DEBUG_PRINT
                        Serial.print("Moving device ID ");
                        Serial.print(id);
                        Serial.print(" to position ");
                        Serial.println(position);
#endif
                    }//end: tuples
                }//end: M
                else
                {
                    if (DEBUG_PRINT)
                        Serial.println("Invalid command length for 'M'");
                }
                break;


            case 'b': // Set baudrate
                // alignAllDevicesBaudrate(int1);
                break;

            case 'd': // Set ID
                // setDeviceId(int1, int2);
                break;

            case 'v': // Set velocity
                // setMaxVelocity(int1, int2);
                break;

            case 'o': // Set mode
                // setDeviceMode(int1, int2);
                break;

            case 'f': // Flash device
                // flashDevice(int1, int2, int3);  // (id, duration, repeats)
                break;

            default:
                if (DEBUG_PRINT)
                    Serial.println("Invalid command");
                break;
            }
        } // EVAL

        // RX
        if (receiving)
        {
            // Store received bytes in buffer
            if (bufferIndex < sizeof(buffer))
            {
                buffer[bufferIndex++] = incomingByte;
            }
        } // RX
    } // while
} // loop

// ----------------------------------------------------------------------
// GETTERS

void scanForDevices() {
  cmd.println("DEBUG: Scanning for devices.");

  int8_t found_dynamixel = 0;

  for(int8_t protocol = 2; protocol < 3; protocol++) {
    dxl.setPortProtocolVersion((float)protocol);
    cmd.print("DEBUG:SCAN PROTOCOL ");
    cmd.println(protocol);

    for(int8_t index = 0; index < MAX_BAUD; index++) {
      cmd.print("DEBUG:SCAN BAUDRATE ");
      cmd.println(buad[index]);
      dxl.begin(buad[index]);

      // Allow time for devices to initialize
      delay(10); // 1 second delay to stabilize communication

      for(int id = 0; id <= MAX_ID; id++) {
        if(dxl.ping(id)) {
          cmd.print("DEBUG: ID : ");
          cmd.print(id);
          cmd.print(", Model Number: ");
          cmd.println(dxl.getModelNumber(id));
          found_dynamixel++;
        }
      }
    }
  }

  cmd.print("DEBUG: Total ");
  cmd.print(found_dynamixel);
  cmd.println(" DYNAMIXEL(s) found!");

  // return to state prior to looping baud rates, etc.
  dxl.begin(dxl_baudrate);
  dxl.setPortProtocolVersion(dxl_protocol_version);
}//end:scanForDevices


String quote_key_value_pair(String key, String value, bool add_trailing_comma)
{
String quotation = "\"";
String entry = quotation + key + quotation + ":" + value;
if (add_trailing_comma) {
    entry += ", ";
}
return entry;
}//end:quote_key_value_pair


String getInfoById(int id) {
  #if DEBUG_PRINT
    cmd.print("DEBUG:getting info for ");
    cmd.println(id);
  #endif

  // Prepare a String to store the information
  String info = "{";

  // id
  info += quote_key_value_pair("id", String(id), true);
//   info += "\"id\": " + String(id) + ", ";

  // Fetch the model number
  uint16_t modelNumber = dxl.getModelNumber(id);
  info += quote_key_value_pair("model_number", String(modelNumber), true);
//   info += "\"model_number\": " + String(modelNumber) + ", ";

//  // Fetch the firmware version
//  float firmwareVersion = dxl.getFirmwareVersion(id);
//  info += "\"firmware_version\": " + String(firmwareVersion, 1) + ", ";

  // Fetch the baud rate (if applicable)
  uint32_t baudRate = dxl.readControlTableItem(BAUD_RATE, id);
//   info += "\"baud_rate\": " + String(baudRate) + ", ";
  info += quote_key_value_pair("baud_rate_int", String(baudRate), true);

  // Fetch the present position in raw
  int presentPositionRaw = dxl.getPresentPosition(id, UNIT_RAW);
//   info += "\"position_raw\": " + String(presentPositionRaw) + ", ";
  info += quote_key_value_pair("position_raw", String(presentPositionRaw), true);

  // Fetch the present position in degrees
  float presentPositionDeg = dxl.getPresentPosition(id, UNIT_DEGREE);
//   info += "\"position_deg\": " + String(presentPositionDeg, 2) + ", ";
  info += quote_key_value_pair("position_deg", String(presentPositionDeg), true);

  // operating mode
  uint8_t mode = dxl.readControlTableItem(OPERATING_MODE, id);
//   info += "\"operating_mode\":" + String(mode) + ", ";
  info += quote_key_value_pair("operating_mode_int", String(mode), true);

  // Fetch the present velocity
  int velocity_max = dxl.readControlTableItem(MOVING_SPEED, id); // Assume this method exists
//   info += "\"velocity_max\": " + String(velocity_max) + ", ";
  info += quote_key_value_pair("velocity_max", String(velocity_max), false);

  // Close the dictionary-like string
  info += "}";

  return info;
}//end:getInfoById


void getPosition(int id)
{
    int positionRaw = dxl.getPresentPosition(id, UNIT_RAW);
    // cmd.println(positionRaw);
    cmd.write((positionRaw >> 8) & 0xFF); // Send high byte
    cmd.write(positionRaw & 0xFF);        // Send low byte
}//end:getPosition



// ----------------------------------------------------------------------
// SETTERS

void setPosition(uint16_t id, uint16_t position)
{
    // Check if ID is within valid range
    if (id < 1 || id > MAX_ID)
    {
        if (DEBUG_PRINT)
            Serial.println("Invalid ID");
        return;
    }

    digitalWrite(move_ttl_pin, HIGH);

    // Move the Dynamixel device
    dxl.setGoalPosition(id, position);

    if (DEBUG_PRINT)
    {
        Serial.print("Moving device ID ");
        Serial.print(id);
        Serial.print(" to position ");
        Serial.println(position);
    }
}

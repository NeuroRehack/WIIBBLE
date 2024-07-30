using System;
using WiimoteLib;

namespace WiiBalanceBoardExample
{
    class Program
    {
        private static Wiimote wiimote = new Wiimote();
        private static bool dataRead = false;

        static void Main(string[] args)
        {
            try
            {
                // Connect to the Wii Balance Board
                wiimote.WiimoteChanged += Wiimote_WiimoteChanged;
                wiimote.WiimoteExtensionChanged += Wiimote_WiimoteExtensionChanged;

                Console.WriteLine("Press the sync button on the Wii Balance Board...");
                wiimote.Connect();
                wiimote.SetReportType(InputReport.IRAccel, true);

                // Set LEDs to indicate a successful connection
                wiimote.SetLEDs(true, false, false, false);

                // Wait until data has been read
                while (!dataRead)
                {
                    System.Threading.Thread.Sleep(10); // Sleep briefly to wait for data reading
                }

                Console.WriteLine("Data successfully read. Exiting...");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
            }
            finally
            {
                wiimote.Disconnect();
            }
        }

        private static void Wiimote_WiimoteExtensionChanged(object sender, WiimoteExtensionChangedEventArgs e)
        {
            if (e.Inserted)
            {
                if (wiimote.WiimoteState.ExtensionType == ExtensionType.BalanceBoard)
                {
                    Console.WriteLine("Balance Board connected.");
                }
            }
            else
            {
                Console.WriteLine("Balance Board disconnected.");
            }
        }

        private static void Wiimote_WiimoteChanged(object sender, WiimoteChangedEventArgs e)
        {
            WiimoteState ws = e.WiimoteState;

            if (ws.ExtensionType == ExtensionType.BalanceBoard)
            {
                BalanceBoardState bbs = ws.BalanceBoardState;
                float weight = bbs.WeightKg;
                // Console.WriteLine($"Weight: {weight:F2} kg");




                float tr = bbs.SensorValuesKg.TopRight;
                float tl = bbs.SensorValuesKg.TopLeft;
                float br = bbs.SensorValuesKg.BottomRight;
                float bl = bbs.SensorValuesKg.BottomLeft;

                // // Optionally, display individual sensor readings:
                // Console.WriteLine($"Top Right: {bbs.SensorValuesKg.TopRight}");
                // Console.WriteLine($"Top Left: {bbs.SensorValuesKg.TopLeft}");
                // Console.WriteLine($"Bottom Right: {bbs.SensorValuesKg.BottomRight}");
                // Console.WriteLine($"Bottom Left: {bbs.SensorValuesKg.BottomLeft}");

                // Set flag to indicate data has been read
                dataRead = true;
            }
        }
    }
}

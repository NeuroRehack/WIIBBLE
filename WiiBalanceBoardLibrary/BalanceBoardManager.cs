using System;
using WiimoteLib;

namespace WiiBalanceBoardLibrary
{
    public class BalanceBoardManager
    {
        private Wiimote wiimote = new Wiimote();
        private bool dataRead = false;

        public event EventHandler<BalanceBoardDataEventArgs> BalanceBoardDataReceived;

        public BalanceBoardManager()
        {
            wiimote.WiimoteChanged += Wiimote_WiimoteChanged;
            wiimote.WiimoteExtensionChanged += Wiimote_WiimoteExtensionChanged;
        }

        public void Connect()
        {
            try
            {
                wiimote.Connect();
                wiimote.SetReportType(InputReport.IRAccel, true);
                wiimote.SetLEDs(true, false, false, false);
            }
            catch (Exception ex)
            {
                throw new Exception($"Error connecting to Wii Balance Board: {ex.Message}");
            }
        }

        public void Disconnect()
        {
            wiimote.Disconnect();
        }

        public bool IsDataRead => dataRead;

        // Property to expose the battery level
        public float BatteryLevel
        {
            get
            {
                // Assuming WiimoteState.Battery provides the battery level as a float between 0.0 and 1.0
                return wiimote.WiimoteState.Battery;
            }
        }

        private void Wiimote_WiimoteExtensionChanged(object sender, WiimoteExtensionChangedEventArgs e)
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

        private void Wiimote_WiimoteChanged(object sender, WiimoteChangedEventArgs e)
        {
            WiimoteState ws = e.WiimoteState;

            if (ws.ExtensionType == ExtensionType.BalanceBoard)
            {
                BalanceBoardState bbs = ws.BalanceBoardState;
                float weight = bbs.WeightKg;

                BalanceBoardDataEventArgs args = new BalanceBoardDataEventArgs
                {
                    Weight = weight,
                    TopRight = bbs.SensorValuesKg.TopRight,
                    TopLeft = bbs.SensorValuesKg.TopLeft,
                    BottomRight = bbs.SensorValuesKg.BottomRight,
                    BottomLeft = bbs.SensorValuesKg.BottomLeft
                };

                BalanceBoardDataReceived?.Invoke(this, args);
                dataRead = true;
            }
        }
    }

    public class BalanceBoardDataEventArgs : EventArgs
    {
        public float Weight { get; set; }
        public float TopRight { get; set; }
        public float TopLeft { get; set; }
        public float BottomRight { get; set; }
        public float BottomLeft { get; set; }
    }
}

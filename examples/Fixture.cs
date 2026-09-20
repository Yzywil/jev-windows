using System;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

// A disposable UIA test application. Never opens user documents or uses the network.
public static class Fixture {
    [STAThread]
    public static void Main(string[] args) {
        string proofPath = args.Length > 0 ? args[0] : Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "proof.txt");
        Application.EnableVisualStyles();
        Form form = new Form { Text = "Jev Windows Test Fixture", Width = 540, Height = 280,
            StartPosition = FormStartPosition.CenterScreen };
        TextBox input = new TextBox { Name = "name", AccessibleName = "Name",
            Location = new Point(24, 30), Width = 460 };
        Button apply = new Button { Name = "apply", Text = "Apply", AccessibleName = "Apply",
            Location = new Point(24, 75) };
        CheckBox option = new CheckBox { Name = "option", Text = "Enable option",
            AccessibleName = "Enable option", Location = new Point(140, 80), Width = 160 };
        Label result = new Label { Name = "result", Text = "Ready",
            Location = new Point(24, 140), Width = 460 };
        TextBox password = new TextBox { Name = "password", AccessibleName = "Protected field",
            UseSystemPasswordChar = true, Text = "synthetic-do-not-send",
            Location = new Point(24, 175), Width = 200 };
        apply.Click += delegate {
            result.Text = "Applied: " + input.Text;
            if (proofPath != null) {
                // An independent fixture-owned oracle: runner cannot write this file.
                File.WriteAllText(proofPath, input.Text, new UTF8Encoding(false));
            }
        };
        form.Controls.AddRange(new Control[] { input, apply, option, result, password });
        Application.Run(form);
    }
}

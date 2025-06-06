/*  This file is part of Chummer5a.
 *
 *  Chummer5a is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Chummer5a is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with Chummer5a.  If not, see <http://www.gnu.org/licenses/>.
 *
 *  You can obtain the full source code for Chummer5a at
 *  https://github.com/chummer5a/chummer5a
 */

using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Chummer.UI.Shared.Components
{
    public partial class DicePoolControl : UserControl
    {
        private int _intDicePool;
        private bool _blnCanBeRolled = true;
        private bool _blnCanEverBeRolled = Utils.IsDesignerMode;

        public DicePoolControl()
        {
            InitializeComponent();
            this.UpdateLightDarkMode();
            this.TranslateWinForm();

            CanEverBeRolled = CanEverBeRolled || GlobalSettings.AllowSkillDiceRolling;
            cmdRoll.Visible = CanBeRolled && CanEverBeRolled;
        }

        private async void DicePoolControl_Load(object sender, EventArgs e)
        {
            await cmdRoll.SetToolTipTextAsync(await LanguageManager.GetStringAsync("Tip_DiceRoller").ConfigureAwait(false)).ConfigureAwait(false);
        }

        private async void cmdRoll_Click(object sender, EventArgs e)
        {
            if (Program.MainForm == null)
                return;
            Character objCharacter = null;
            if (await this.DoThreadSafeFuncAsync(x => x.ParentForm).ConfigureAwait(false) is CharacterShared frmParent)
                objCharacter = frmParent.CharacterObject;
            await Program.MainForm.OpenDiceRollerWithPool(objCharacter, DicePool).ConfigureAwait(false);
        }

        public void SetLabelToolTip(string caption)
        {
            lblDicePool.SetToolTip(caption);
        }

        public Task SetLabelToolTipAsync(string caption, CancellationToken token = default)
        {
            return lblDicePool.SetToolTipAsync(caption, token);
        }

        public bool CanBeRolled
        {
            get => _blnCanBeRolled;
            set
            {
                if (_blnCanBeRolled == value)
                    return;
                _blnCanBeRolled = value;
                cmdRoll.Visible = value && CanEverBeRolled;
            }
        }

        public bool CanEverBeRolled
        {
            get => _blnCanEverBeRolled;
            set
            {
                if (_blnCanEverBeRolled == value)
                    return;
                _blnCanEverBeRolled = value;
                cmdRoll.Visible = value && CanBeRolled;
            }
        }

        public int DicePool
        {
            get => _intDicePool;
            set
            {
                if (Interlocked.Exchange(ref _intDicePool, value) == value)
                    return;
                lblDicePool.Text = CanBeRolled
                    ? value.ToString(GlobalSettings.CultureInfo)
                    : value.ToString("+#,0;-#,0;0", GlobalSettings.CultureInfo);
            }
        }

        public string ToolTipText
        {
            get => lblDicePool.ToolTipText;
            set => lblDicePool.ToolTipText = value;
        }

        public Task SetToolTipTextAsync(string value, CancellationToken token = default) =>
            lblDicePool.SetToolTipTextAsync(value, token);

        public ToolTip ToolTipObject => lblDicePool.ToolTipObject;
    }
}

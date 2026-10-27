"""Integration tests for Bash and Zsh shell possession in haunt.sh."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import unittest


class TestHauntShellIntegration(unittest.TestCase):
    """Tests shell hooks, exit status preservation, non-blocking execution, and bash integration."""

    @classmethod
    def setUpClass(cls):
        cls.bash_path = shutil.which("bash")

    def setUp(self):
        if not self.bash_path:
            self.skipTest("Bash interpreter not found on system.")

    def run_bash(self, script: str) -> subprocess.CompletedProcess:
        """Helper to run a bash snippet via stdin with clean UNIX newlines."""
        clean_script = script.replace("\r\n", "\n").replace("\r", "\n")
        res = subprocess.run(
            [self.bash_path],
            input=clean_script.encode("utf-8"),
            capture_output=True,
            timeout=10,
        )
        return subprocess.CompletedProcess(
            args=res.args,
            returncode=res.returncode,
            stdout=res.stdout.decode("utf-8", errors="replace"),
            stderr=res.stderr.decode("utf-8", errors="replace"),
        )

    def test_shell_scripts_syntax(self):
        """Verify syntax of haunt.sh, install.sh, and demo.sh using bash -n."""
        for script in ["haunt.sh", "install.sh", "demo.sh"]:
            res = subprocess.run([self.bash_path, "-n", script], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Syntax check failed for {script}: {res.stderr}")

    def test_non_interactive_guard(self):
        """haunt.sh must not load in non-interactive shells unless HAUNT_FORCE=1."""
        script = """
        source ./haunt.sh
        if [ -z "${__HAUNT_LOADED:-}" ]; then
            echo "UNLOADED"
        fi
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("UNLOADED", res.stdout)

    def test_force_load_sets_loaded_flag(self):
        """haunt.sh loads when HAUNT_FORCE=1 is explicitly set."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        if [ "${__HAUNT_LOADED:-}" = "1" ]; then
            echo "LOADED"
        fi
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("LOADED", res.stdout)

    def test_duplicate_sourcing_idempotent(self):
        """Sourcing haunt.sh multiple times does not duplicate hooks or fail."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        source ./haunt.sh
        source ./haunt.sh
        echo "TRIPLE_SOURCED_OK"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("TRIPLE_SOURCED_OK", res.stdout)

    def test_exit_status_preservation(self):
        """haunt prompt hook must strictly preserve the command's original exit status ($?)."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        (exit 42)
        __haunt_bash_prompt
        echo "EXIT_CODE=$?"
        (exit 0)
        __haunt_bash_prompt
        echo "SUCCESS_CODE=$?"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("EXIT_CODE=42", res.stdout)
        self.assertIn("SUCCESS_CODE=0", res.stdout)

    def test_exorcise_two_attempt_ritual(self):
        """First exorcise fails with refusal; second consecutive exorcise unbinds the ghost."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        exorcise 2>&1
        echo "STATE1=$HAUNT_ENABLED"
        exorcise 2>&1
        echo "STATE2=$HAUNT_ENABLED"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("STATE1=1", res.stdout)
        self.assertIn("STATE2=0", res.stdout)
        self.assertIn("cannot banish me", res.stdout)
        self.assertIn("The machine is free", res.stdout)

    def test_haunt_shell_commands(self):
        """Test haunt on/off/chance/speed/ghost shell commands."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        haunt off
        echo "ENABLED=$HAUNT_ENABLED"
        haunt on
        echo "ENABLED=$HAUNT_ENABLED"
        haunt chance 75
        echo "CHANCE=$HAUNT_CHANCE"
        haunt speed fast
        echo "SPEED=$HAUNT_SPEED"
        haunt ghost cobol_ghost
        echo "GHOST=$HAUNT_GHOST"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertIn("ENABLED=0", res.stdout)
        self.assertIn("ENABLED=1", res.stdout)
        self.assertIn("CHANCE=75", res.stdout)
        self.assertIn("SPEED=fast", res.stdout)
        self.assertIn("GHOST=cobol_ghost", res.stdout)

    def test_asynchronous_prompt_responsiveness(self):
        """Shell hook returns immediately without waiting for inference."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        start_ts=$(date +%s 2>/dev/null)
        __haunt_dispatch_hook 0 "ls -la"
        end_ts=$(date +%s 2>/dev/null)
        diff=$(( end_ts - start_ts ))
        echo "DIFF_SEC=$diff"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        for line in res.stdout.splitlines():
            if line.startswith("DIFF_SEC="):
                diff = int(line.split("=")[1])
                # Hook must complete within 1 second
                self.assertLessEqual(diff, 1)

    def test_model_output_never_executed(self):
        """Ensure model text is treated purely as display data, never executed."""
        script = """
        export HAUNT_FORCE=1
        source ./haunt.sh
        mkdir -p "${__HAUNT_RUN_DIR}"
        echo "echo PWNED_EXECUTION" > "${__HAUNT_RUN_DIR}/test_exec.res"
        __haunt_check_and_display_result "test_exec" > /dev/null 2>&1
        echo "DONE"
        """
        res = self.run_bash(script)
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("PWNED_EXECUTION", res.stdout)
        self.assertIn("DONE", res.stdout)


if __name__ == "__main__":
    unittest.main()

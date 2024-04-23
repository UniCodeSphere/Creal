from pathlib import Path
from dataclasses import dataclass
import re
import subprocess
import tempfile
from itertools import chain
from pathlib import Path
from shutil import which

from diopter.utils import CommandOutput, run_cmd, run_cmd_async, temporary_file
from diopter.compiler import SourceProgram, Language, CompileError


@dataclass(frozen=True, kw_only=True)
class CComp:
    """A ccomp(compcert) instance.

    Attributes:
        exe (Path): path to compcert/ccomp
    """

    exe: Path
    # TODO: timeout_s: int = 8

    @staticmethod
    def get_system_ccomp():
        """Returns:
        CComp:
            the system's ccomp
        """

        ccomp = which("ccomp")
        if not ccomp:
            return None
        return CComp(exe=Path(ccomp).resolve(strict=True))

    def check_program(
        self, program: SourceProgram, timeout: int | None = None, debug: bool = False,
        additional_flags: list[str] = [],
    ) -> bool:
        """Checks the input program for errors using ccomp's interpreter mode.

        Args:
           program (SourceProgram): the input program
           timeout (int | None): timeout in seconds for the checking
           debug (bool): if true ccomp's output will be printed on failure

        Returns:
            bool:
                was the check successful?
        """
        assert program.language == Language.C

        # ccomp doesn't like these
        code = re.sub(r"__asm__ [^\)]*\)", r"", program.get_modified_code())

        tf = temporary_file(contents=code, suffix=".c")
        cmd = (
            [
                str(self.exe),
                str(tf.name),
                "-interp",
                "-fall",
            ]
            + [
                f"-I{ipath}"
                for ipath in chain(program.include_paths, program.system_include_paths)
            ]
            + [f"-D{macro}" for macro in program.defined_macros]
            + additional_flags
        )
        try:
            result = run_cmd(
                cmd,
                additional_env={"TMPDIR": str(tempfile.gettempdir())},
                timeout=timeout,
            )
        except subprocess.CalledProcessError as e:
            if debug:
                print(CompileError.from_called_process_exception(" ".join(cmd), e))
            return False
        return result
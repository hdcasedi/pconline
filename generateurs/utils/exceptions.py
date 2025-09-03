from dataclasses import dataclass


@dataclass
class LatexCompileError(Exception):
    message: str
    stdout: str = ""
    log_tail: str = ""
    hint: str = ""

    def __str__(self) -> str:  # pragma: no cover - simple join
        parts = [self.message]
        if self.hint:
            parts.append(f"\nHint: {self.hint}")
        if self.log_tail:
            parts.append("\n--- log tail ---\n" + self.log_tail)
        return "\n".join(parts)



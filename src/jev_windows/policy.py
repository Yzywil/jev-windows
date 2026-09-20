"""Local grants, never model-produced permissions. Heuristics are not a security boundary."""

import re
import unicodedata

from .contracts import Candidate, Task

SENSITIVE = re.compile(
    r"delete|remove|erase|format|send|submit|publish|upload|pay|purchase|buy|checkout|"
    r"subscribe|install|permission|authorize|password|credential|sign.?in|log.?in|"
    r"删除|移除|清空|格式化|发送|提交|发布|上传|支付|购买|订阅|安装|授权|权限|密码|登录",
    re.IGNORECASE,
)


def normalized_label(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf"
    )


def needs_confirmation(task: Task, candidate: Candidate) -> bool:
    e = candidate.element
    if SENSITIVE.search(normalized_label(e.name + " " + e.automation_id)):
        return True
    return not any(
        g.operation == candidate.operation and g.selector.matches(e) for g in task.grants
    )

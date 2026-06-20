import re
import copy


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****5678"""
    if not phone or len(phone) < 7:
        return phone
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 11:
        return digits[:3] + "****" + digits[-4:]
    return phone


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏：110***********1234"""
    if not id_card or len(id_card) < 8:
        return id_card
    return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]


def mask_email(email: str) -> str:
    """邮箱脱敏：zh***@example.com"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


def desensitize(parsed_data: dict) -> dict:
    """对简历结构化数据进行脱敏处理。"""
    result = copy.deepcopy(parsed_data)
    if "phone" in result and result["phone"]:
        result["phone"] = mask_phone(result["phone"])
    if "id_card" in result and result["id_card"]:
        result["id_card"] = mask_id_card(result["id_card"])
    if "email" in result and result["email"]:
        result["email"] = mask_email(result["email"])
    return result

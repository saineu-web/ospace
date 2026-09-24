from django import template

register = template.Library()


@register.filter
def agreement_blocks(body: str):
    """Split agreement text into ("h", heading) / ("p", paragraph) tuples. '# ' starts a heading."""
    out = []
    for block in (body or "").replace("\r\n", "\n").split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):
            out.append(("h", block[2:].strip()))
        else:
            out.append(("p", block))
    return out

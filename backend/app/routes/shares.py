import base64
import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from app.deps import get_db
from app.storage import DepsDB

router = APIRouter()


class CreateShareRequest(BaseModel):
    username: str = "user"
    svg_data: str
    png_base64: Optional[str] = ""
    title: Optional[str] = ""


class Share(BaseModel):
    share_id: str
    page_url: str
    svg_url: str
    png_url: str
    og_url: str
    markdown: str


@router.post("/api/shares", response_model=Share)
@router.post("/api/share", response_model=Share)
async def create_share_endpoint(
    req: CreateShareRequest,
    request: Request,
    db: DepsDB = Depends(get_db),
):
    share_id = f"s_{uuid.uuid4().hex[:8]}"
    await db.create_share(
        username=req.username,
        base64=req.png_base64 or "",
        svg_data=req.svg_data,
        share_id=share_id,
    )

    base_url = str(request.base_url).rstrip("/")
    page_url = f"{base_url}/s/{share_id}"
    svg_url = f"{base_url}/s/{share_id}/cloud.svg"
    png_url = f"{base_url}/s/{share_id}/cloud.png"
    og_url = png_url

    title = req.title or f"{req.username}'s Tech Stack"
    markdown = f"[![{title}]({svg_url})]({page_url})"

    return Share(
        share_id=share_id,
        page_url=page_url,
        svg_url=svg_url,
        png_url=png_url,
        og_url=og_url,
        markdown=markdown,
    )


@router.get("/s/{share_id}/cloud.svg")
async def share_cloud_svg(share_id: str, db: DepsDB = Depends(get_db)):
    svg_data = await db.fetch_svg(share_id)
    if not svg_data:
        raise HTTPException(status_code=404, detail="Share not found")
    return Response(
        content=svg_data,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
            "Content-Disposition": "inline",
        },
    )


@router.get("/s/{share_id}/cloud.png")
@router.get("/s/{share_id}/og.png")
async def share_cloud_png(share_id: str, db: DepsDB = Depends(get_db)):
    raw_b64 = await db.fetch_png(share_id)
    if not raw_b64:
        raise HTTPException(status_code=404, detail="PNG not available for this share")

    # Clean data URL prefix if present
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        png_bytes = base64.b64decode(raw_b64)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decode image")


@router.get("/s/{share_id}", response_class=HTMLResponse)
async def public_share_page(
    share_id: str,
    request: Request,
    db: DepsDB = Depends(get_db),
):
    svg_data = await db.fetch_svg(share_id)
    if not svg_data:
        raise HTTPException(status_code=404, detail="Share not found")

    base_url = str(request.base_url).rstrip("/")
    og_url = f"{base_url}/s/{share_id}/cloud.png"
    svg_url = f"{base_url}/s/{share_id}/cloud.svg"

    og_image_tags = ""
    if await db.fetch_png(share_id):
        og_image_tags = (
            f'  <meta property="og:image" content="{og_url}" />\n'
            f'  <meta name="twitter:image" content="{og_url}" />\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tech Stack Cloud — LibCloud</title>
  <meta property="og:title" content="Tech Stack Cloud — LibCloud" />
  <meta property="og:description" content="View this developer's interactive dependency logo cloud." />
{og_image_tags}  <meta name="twitter:card" content="summary_large_image" />
  <style>
    body {{
      margin: 0;
      background: #090d16;
      color: #e2e8f0;
      font-family: system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      box-sizing: border-box;
    }}
    .container {{
      max-width: 960px;
      width: 100%;
      text-align: center;
    }}
    .cloud-box {{
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 16px;
      padding: 24px;
      margin: 20px 0;
      box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }}
    .cloud-box img {{
      max-width: 100%;
      height: auto;
    }}
    a.btn {{
      display: inline-block;
      margin-top: 12px;
      background: #38bdf8;
      color: #0f172a;
      font-weight: 600;
      padding: 10px 20px;
      border-radius: 8px;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="cloud-box">
      <img src="{svg_url}" alt="Logo Cloud" />
    </div>
    <a class="btn" href="/">Generate Your Own Cloud →</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


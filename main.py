from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Employee Monitor")

# =====================
# 静态文件
# =====================
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# =====================
# 内存数据
# =====================
EMPLOYEES = {}

# =====================
# 页面
# =====================
@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

# =====================
# 员工上报（完全兼容当前 agent）
# =====================
@app.post("/api/report")
async def report(request: Request):
    data = await request.json()

    employee = data.get("employee", {})
    temps = data.get("temps", {})

    employee_id = employee.get("employee_id", "unknown")
    ip_address = employee.get("ip_address", "unknown")

    EMPLOYEES[employee_id] = {
        "employee": employee,
        "temps": temps,
        "ip_address": ip_address,
        "last_seen": datetime.utcnow().timestamp()
    }

    return {"status": "ok"}

# =====================
# 前端获取数据
# =====================
@app.get("/data")
def get_data():
    return {"employees": EMPLOYEES}

# =====================
# 清空数据
# =====================
@app.post("/api/clear")
def clear_all():
    EMPLOYEES.clear()
    return {"status": "ok", "message": "所有员工数据已清空"}

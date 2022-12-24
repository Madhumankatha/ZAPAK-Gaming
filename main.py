from datetime import datetime
from unicodedata import name
from fastapi import FastAPI, Request, Cookie
from fastapi.params import Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import starlette.status as status
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dbcontroller import DBController

# creating a FastAPI object
app = FastAPI()
security = HTTPBasic()

# configuring the static, which serve static
app.mount("/static", StaticFiles(directory="static"), name="static")

# adding the Session Middleware
app.add_middleware(SessionMiddleware, secret_key='MyApp')

# configuring the HTML pages
templates = Jinja2Templates(directory="templates")

#constant name for DATABASE_NAME
DATABASE_NAME = "app.db"
db = DBController(DATABASE_NAME)

# declaring urls
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.get("/shop", response_class=HTMLResponse)
def shop(request: Request):
    plants = db.executeQuery("select * from products")
    return templates.TemplateResponse("shop.html", {"request": request, "plants": plants})


@app.get("/details/{pid}", response_class=HTMLResponse)
def detail(request: Request, pid: int):
    if not request.session.get('isLogin'):
        return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)
    description = db.executeQueryWithParams("select * from products where id =?", [pid])
    return templates.TemplateResponse("details.html", {"request": request, "pid": pid, "description": description[0]})


@app.get("/register",response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
def do_register(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...),
                address: str = Form(...), phone: str = Form(...)):
    user = {"username":username,"password":password,"email":email,"address":address,"phone":phone}
    db.insert("users",user)    
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)


@app.get("/login",response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def do_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = db.executeQueryWithParams("select * from users where username =? and password=?", [username, password])[0]
    if not user:
        return templates.TemplateResponse("/login.html", {"request": request, "msg": "Invalid Username or Password"})
    else:
        request.session.setdefault("isLogin", True)
        request.session.setdefault('username', user['username'])
        request.session.setdefault('uid', user['id'])
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@app.get("/addtocart", response_class=HTMLResponse)
async def addtocart(request: Request, pid:int = 1, qty:int = 1):
    uid = request.session.get('uid')
    cart = {"pid":pid,"qty": qty, "uid": uid}
    db.insert("carts",cart)
    return RedirectResponse("/cart", status_code=status.HTTP_302_FOUND)

@app.get("/cart", response_class=HTMLResponse)
def cart(request: Request):
    if not request.session.get('isLogin'):
        return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)

    uid = request.session.get('uid')
    items = db.executeQueryWithParams("SELECT *,c.id as cid from USERS u,carts c, products p where u.id=c.uid and c.pid=p.id and c.uid =?", [uid])
    return templates.TemplateResponse("/cart.html", {"request": request, "items": items})


@app.get("/deletecart/{cid}", response_class=HTMLResponse)
def delete_cart_item(request: Request, cid: int):
    db.executeQueryWithParams("Delete from carts where id =?", [cid])
    return RedirectResponse("/cart", status_code=status.HTTP_302_FOUND)


@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)


@app.get("/confrim", response_class=HTMLResponse)
def confrim(request: Request):
    uid = request.session.get('uid')
    carts = db.executeQueryWithParams("SELECT * from carts where uid = ? ",[uid])
    for cart in carts:
        now = datetime.now()
        order_time = now.strftime("%d/%m/%Y %H:%M:%S")
        order = {"pid":cart[1],"qty":cart[2],"uid":cart[3],"status":"ORDERED","date":order_time}
        db.insert("orders",order)
    db.executeQueryWithParams("Delete from carts where uid = ? ", [uid])
    return RedirectResponse("/orders", status_code=status.HTTP_302_FOUND)


@app.get("/orders",response_class=HTMLResponse)
def orders(request : Request):
    if not request.session.get('isLogin'):
        return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)

    uid = request.session.get('uid')

    orders = db.executeQueryWithParams("SELECT *,o.id as oid from USERS u,orders o, products p where u.id=o.uid and o.pid=p.id and o.uid =?",
                [uid])
    return templates.TemplateResponse("/orders.html", {"request": request, "orders": orders})


@app.get("/admin/", response_class=HTMLResponse)
def admin_index(request: Request):
    return templates.TemplateResponse("/admin/index.html", {"request": request})


@app.post("/admin/", response_class=HTMLResponse)
def admin_index(request: Request, username: str = Form(...), password: str = Form(...)):
    admin = db.executeQueryWithParams("select * from admin where username =? and password=?", [username, password])[0]
    if not admin:
        return templates.TemplateResponse("/admin/index.html", {"request": request, "msg": "Invalid Username or Password"})
    else:
        request.session.setdefault("isLogin", True)
        request.session.setdefault('username', admin['username'])
        request.session.setdefault('uid', admin['id'])
        request.session.setdefault('role', admin['role'])
        return RedirectResponse("/admin/dashboard", status_code=status.HTTP_302_FOUND)


@app.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("/admin/dashboard.html", {"request": request })


@app.get("/admin/products", response_class=HTMLResponse)
def admin_products(request: Request):
    products = db.executeQuery("select * from products")
    return templates.TemplateResponse("/admin/products.html", {"request": request, "products": products})


@app.get("/admin/products/create", response_class=HTMLResponse)
def admin_products_create(request: Request):
    return templates.TemplateResponse("/admin/products_create.html", {"request": request})


@app.post("/admin/products/create", response_class=HTMLResponse)
def admin_products_create(request: Request, pname:str = Form(...), price: str = Form(...), image: str = Form(...), details: str = Form(...), tags: str = Form(...), category:str = Form(...)):
    product = {"name":pname,"price":price,"details":details,"image":image,"tags":tags,"category":category}
    db.insert("products",product)
    return RedirectResponse("/admin/products",status_code=status.HTTP_302_FOUND)


@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request):
    orders = db.executeQuery("SELECT *, o.id as oid from users u, products p, orders o where o.uid = u.id and o.pid = p.id")
    return templates.TemplateResponse("/admin/orders.html", {"request": request, "orders": orders})


@app.get("/admin/logout", response_class=HTMLResponse)
def admin_logout(request: Request):
    return templates.TemplateResponse("/admin/logout", {"request": request})


@app.get("/admin/products_edit/{pid}", response_class=HTMLResponse)
def admin_product_edit(request: Request, pid: int = 0):
    return templates.TemplateResponse("/admin/products_edit.html", {"request": request})


@app.get("/admin/products_delete/{pid}", response_class=HTMLResponse)
def admin_product_delete(request: Request, pid: int = 0):
    return RedirectResponse("/admin/products", status_code=status.HTTP_302_FOUND)


@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request):
    return templates.TemplateResponse("/admin/orders.html", {"request": request})


@app.get("/admin/orders_view/{oid}", response_class=HTMLResponse)
def admin_order_view(request: Request, oid: int = 0):
    return templates.TemplateResponse("/admin/orders_view.html", {"request": request})


@app.get("/products", response_class=HTMLResponse)
def products(request: Request):
    products = db.executeQuery("select * from products")
    return templates.TemplateResponse("/products.html", {"request" : request, "products": products })  

@app.get("/view/{pid}", response_class=HTMLResponse)
def view(request: Request, pid: int = 0): 
    product = db.executeQueryWithParams("select * from products where id =?", [pid])
    return templates.TemplateResponse("/view.html", {"request": request, "product": product[0]}) 
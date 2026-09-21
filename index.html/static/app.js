let products=[], cart=JSON.parse(localStorage.getItem('cart')||'[]'), user=null;
const $=s=>document.querySelector(s);
const money=n=>'$'+Number(n).toFixed(2);

async function api(url,opt={}){
  let r=await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json'},...opt});
  let d=await r.json();
  if(!r.ok) throw new Error(d.message||'Request failed');
  return d;
}

async function boot(){
  try{
    let d=await api('/api/auth/me');
    if(d.user){ user=d.user; showApp(); }
    else showLogin();
  }catch{ showLogin(); }
}

function showLogin(){
  $('#authScreen').hidden=false;
  $('#appShell').hidden=true;
}

function showApp(){
  $('#authScreen').hidden=true;
  $('#appShell').hidden=false;
  updateHeader();
  loadProducts();
}

function updateHeader(){
  $('#userLabel').textContent=user?'Hi, '+user.name:'';
  $('#adminNav').hidden=!user || user.role!=='ADMIN';
  updateCartCount();
}

function show(id){
  document.querySelectorAll('.page').forEach(x=>x.hidden=true);
  $('#'+id).hidden=false;
  if(id==='orders')loadOrders();
  if(id==='admin')loadAdmin();
  if(id==='shop')loadProducts();
}

async function loadProducts(){
  try{
    products=(await api('/api/products')).products;
    renderProducts();
  }catch(e){ $('#products').innerHTML='<div class="error">'+e.message+'</div>'; }
}

function renderProducts(){
  let q=($('#search')?.value||'').toLowerCase();
  let list=products.filter(p=>(p.name+' '+p.category+' '+p.description).toLowerCase().includes(q));
  $('#products').innerHTML=list.map(p=>`<article class="product"><img src="${p.image_url}" alt="${p.name}"><div class="product-body"><span class="muted">${p.category}</span><h3>${p.name}</h3><div class="muted">${p.description}</div><div class="price">${money(p.price)}</div><div class="row"><span class="stock">${p.stock} in stock</span><button class="primary" ${p.stock<1?'disabled':''} onclick="addToCart(${p.id})">Add to cart</button></div></div></article>`).join('')||'<div class="empty">No products found.</div>';
}

function addToCart(id){
  let p=products.find(x=>x.id===id);
  let x=cart.find(i=>i.product_id===id);
  if(x)x.quantity++; else cart.push({product_id:id,quantity:1,product:p});
  saveCart(); toast('Added to cart');
}
function saveCart(){localStorage.setItem('cart',JSON.stringify(cart));updateCartCount()}
function updateCartCount(){$('#cartCount').textContent=cart.reduce((a,x)=>a+x.quantity,0)}

function openCart(){
  let items=cart;
  $('#modalContent').innerHTML=`<h2>Your Cart</h2>${items.length?items.map((x,i)=>`<div class="cart-item"><img src="${x.product.image_url}"><div style="flex:1"><b>${x.product.name}</b><div class="muted">${money(x.product.price)} × ${x.quantity}</div></div><button class="small-btn danger" onclick="removeCart(${i})">Remove</button></div>`).join('')+`<h3>Total: ${money(items.reduce((a,x)=>a+x.product.price*x.quantity,0))}</h3><button class="primary" onclick="checkout()">Proceed to Checkout</button>`:'<div class="empty">Your cart is empty.</div>'}`;
  $('#modal').hidden=false;
}
function removeCart(i){cart.splice(i,1);saveCart();openCart()}

function checkout(){
  if(!user)return showLogin();
  if(!cart.length)return;
  $('#modalContent').innerHTML=`<h2>Checkout</h2><p class="muted">Order total: <b>${money(cart.reduce((a,x)=>a+x.product.price*x.quantity,0))}</b></p><form class="auth-form" onsubmit="placeOrder(event)"><textarea id="address" placeholder="Shipping address" required></textarea><button class="primary">Place Order</button></form>`;
}

async function placeOrder(e){
  e.preventDefault();
  try{
    let d=await api('/api/orders',{method:'POST',body:JSON.stringify({shipping_address:$('#address').value,items:cart.map(x=>({product_id:x.product_id,quantity:x.quantity}))})});
    cart=[];saveCart();
    $('#modalContent').innerHTML=`<div class="empty"><div style="font-size:50px">✓</div><h2>Order #${d.order_id} placed!</h2><p>We received your order successfully.</p><button class="primary" onclick="closeModal();show('orders')">Track Order</button></div>`;
    await loadProducts();
  }catch(e){alert(e.message)}
}

async function loadOrders(){
  if(!user){$('#ordersList').innerHTML='<div class="empty">Please login to see your orders.</div>';return}
  let d=await api('/api/orders');
  $('#ordersList').innerHTML=d.orders.length?d.orders.map(o=>`<div class="order"><div class="row"><div><b>Order #${o.id}</b><div class="muted">${new Date(o.created_at).toLocaleString()}</div></div><span class="status">${o.status}</span></div><p>${o.items.map(i=>`${i.name} × ${i.quantity}`).join(' • ')}</p><b>${money(o.total)}</b><div class="timeline">${['PLACED','PROCESSING','SHIPPED','DELIVERED'].map(s=>`<span title="${s}" class="dot ${['PLACED','PROCESSING','SHIPPED','DELIVERED'].indexOf(s)<=['PLACED','PROCESSING','SHIPPED','DELIVERED'].indexOf(o.status)?'active':''}"></span>`).join('')}</div></div>`).join(''):'<div class="empty">No orders yet.</div>';
}

function showRegister(){
  $('#authTitle').textContent='Create your account';
  $('#authSubtitle').textContent='Join ShopSphere to shop, save your cart and track orders.';
  $('#loginForm').hidden=true;
  $('#registerForm').hidden=false;
  $('#authSwitchText').innerHTML='Already have an account? <button type="button" onclick="showLoginForm()">Sign in</button>';
  $('#authMessage').hidden=true;
}

function showLoginForm(){
  $('#authTitle').textContent='Sign in to your account';
  $('#authSubtitle').textContent='Access your cart, orders and personalized shopping experience.';
  $('#loginForm').hidden=false;
  $('#registerForm').hidden=true;
  $('#authSwitchText').innerHTML='New to ShopSphere? <button type="button" onclick="showRegister()">Create an account</button>';
  $('#authMessage').hidden=true;
}

function showAuthMessage(message){
  $('#authMessage').textContent=message;
  $('#authMessage').hidden=false;
}

function useDemoLogin(){
  $('#loginEmail').value='admin@shop.com';
  $('#loginPassword').value='admin123';
  showLoginForm();
  $('#loginForm').requestSubmit();
}

async function login(e){
  e.preventDefault();
  try{
    let d=await api('/api/auth/login',{method:'POST',body:JSON.stringify({email:$('#loginEmail').value,password:$('#loginPassword').value})});
    user=d.user; showApp(); toast('Signed in successfully');
  }catch(e){showAuthMessage(e.message)}
}

async function register(e){
  e.preventDefault();
  try{
    let d=await api('/api/auth/register',{method:'POST',body:JSON.stringify({name:$('#regName').value,email:$('#regEmail').value,password:$('#regPassword').value})});
    user=d.user; showApp(); toast('Account created successfully');
  }catch(e){showAuthMessage(e.message)}
}

async function logout(){
  try{await api('/api/auth/logout',{method:'POST'})}catch{}
  user=null; cart=[]; saveCart(); showLogin(); showLoginForm(); toast('Logged out');
}

async function loadAdmin(){
  if(!user||user.role!=='ADMIN'){show('shop');return}
  let [s,p,o]=await Promise.all([api('/api/admin/stats'),api('/api/products'),api('/api/admin/orders')]);
  $('#stats').innerHTML=Object.entries(s.stats).map(([k,v])=>`<div class="stat"><span class="muted">${k.toUpperCase()}</span><b>${k==='revenue'?money(v):v}</b></div>`).join('');
  $('#adminProducts').innerHTML=p.products.map(x=>`<div class="admin-item"><div><b>${x.name}</b><div class="muted">${money(x.price)} · Stock ${x.stock}</div></div><button class="small-btn danger" onclick="deleteProduct(${x.id})">Delete</button></div>`).join('');
  $('#adminOrders').innerHTML=o.orders.map(x=>`<div class="admin-item"><div><b>#${x.id} · ${x.user_name}</b><div class="muted">${money(x.total)} · ${x.email}</div></div><select onchange="updateOrder(${x.id},this.value)">${['PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED'].map(s=>`<option ${s===x.status?'selected':''}>${s}</option>`).join('')}</select></div>`).join('');
}

$('#productForm').addEventListener('submit',async e=>{
  e.preventDefault();
  let f=new FormData(e.target),d=Object.fromEntries(f);
  try{await api('/api/products',{method:'POST',body:JSON.stringify(d)});e.target.reset();await loadAdmin();await loadProducts();toast('Product added')}catch(e){alert(e.message)}
});
async function deleteProduct(id){if(!confirm('Delete this product?'))return;try{await api('/api/products/'+id,{method:'DELETE'});loadAdmin();loadProducts()}catch(e){alert(e.message)}}
async function updateOrder(id,status){try{await api('/api/admin/orders/'+id,{method:'PUT',body:JSON.stringify({status})});toast('Order updated')}catch(e){alert(e.message)}}
function closeModal(){$('#modal').hidden=true}
$('#modal').addEventListener('click',e=>{if(e.target.id==='modal')closeModal()});
function toast(t){let x=document.createElement('div');x.textContent=t;x.className='toast';document.body.appendChild(x);setTimeout(()=>x.remove(),1800)}
boot();

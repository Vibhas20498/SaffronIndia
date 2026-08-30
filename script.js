// Collection Filtering and Sorting
document.addEventListener('DOMContentLoaded', function() {
  initializeCollectionFilters();
});

function initializeCollectionFilters() {
  const filterTabs = document.querySelectorAll('.filter-tab');
  const sortSelect = document.getElementById('sort-select');
  const productGrid = document.getElementById('products-grid');
  
  if (!filterTabs.length || !sortSelect || !productGrid) return;
  
  // Filter functionality
  filterTabs.forEach(tab => {
    tab.addEventListener('click', function() {
      // Update active state
      filterTabs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      
      // Filter products
      const filter = this.dataset.filter;
      filterProducts(filter);
    });
  });
  
  // Sort functionality
  sortSelect.addEventListener('change', function() {
    const sortValue = this.value;
    sortProducts(sortValue);
  });
}

function filterProducts(category) {
  const productCards = document.querySelectorAll('.product-card');
  
  productCards.forEach(card => {
    if (category === 'all') {
      card.style.display = 'block';
      animateCard(card);
    } else {
      const cardCategory = card.dataset.category;
      if (cardCategory === category) {
        card.style.display = 'block';
        animateCard(card);
      } else {
        card.style.display = 'none';
      }
    }
  });
}

function sortProducts(sortType) {
  const productGrid = document.getElementById('products-grid');
  const productCards = Array.from(productGrid.querySelectorAll('.product-card'));
  
  productCards.sort((a, b) => {
    switch(sortType) {
      case 'price-low':
        return parseInt(a.dataset.price) - parseInt(b.dataset.price);
      case 'price-high':
        return parseInt(b.dataset.price) - parseInt(a.dataset.price);
      case 'rating':
        const ratingA = a.querySelector('.rating-count').textContent;
        const ratingB = b.querySelector('.rating-count').textContent;
        const reviewsA = parseInt(ratingA.match(/\d+/)[0]);
        const reviewsB = parseInt(ratingB.match(/\d+/)[0]);
        return reviewsB - reviewsA;
      case 'featured':
      default:
        // Keep original order for featured
        return 0;
    }
  });
  
  // Re-append sorted cards
  productCards.forEach(card => {
    productGrid.appendChild(card);
    animateCard(card);
  });
}

function animateCard(card) {
  card.style.animation = 'none';
  setTimeout(() => {
    card.style.animation = 'scaleIn 0.4s ease-out';
  }, 10);
}

const STORAGE_KEY = 'saffronindia-cart';
const ORDER_STORAGE_KEY = 'saffron-orders';
const API_BASE_URL = window.API_BASE_URL || 'http://127.0.0.1:5000';

const postJSON = async (endpoint, payload) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || 'Request failed');
  }
  return data;
};

const getJSON = async (endpoint) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'GET',
    credentials: 'include',
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || 'Request failed');
  }
  return data;
};


const getStoredOrders = () => {
  try {
    return JSON.parse(localStorage.getItem(ORDER_STORAGE_KEY)) || {};
  } catch {
    return {};
  }
};

const saveOrders = (orders) => {
  localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(orders));
};

const saveOrderForEmail = (email, order) => {
  const normalizedEmail = normalizeEmail(email);
  if (!normalizedEmail) return;
  const orders = getStoredOrders();
  if (!orders[normalizedEmail]) {
    orders[normalizedEmail] = [];
  }
  orders[normalizedEmail].push(order);
  saveOrders(orders);
};

const getOrdersForEmail = (email) => {
  const normalizedEmail = normalizeEmail(email);
  if (!normalizedEmail) return [];
  const orders = getStoredOrders();
  return orders[normalizedEmail] || [];
};

const normalizeEmail = (email) => (email ? email.trim().toLowerCase() : '');

const generateOrderId = () => {
  const timestamp = Date.now().toString();
  return `SI-${timestamp.slice(-8)}`;
};

let currentReceiptOrder = null;

const getCart = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
};

const saveCart = (cart) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
};

const addToCart = (product, price) => {
  const cart = getCart();
  const existing = cart.find((item) => item.product === product);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ product, price: Number(price), qty: 1 });
  }
  saveCart(cart);
  alert(`${product} added to cart.`);
  renderCart();
  renderCheckoutSummary();
};

const removeFromCart = (product) => {
  const cart = getCart().filter((item) => item.product !== product);
  saveCart(cart);
  renderCart();
  renderCheckoutSummary();
};

const renderCart = () => {
  const list = document.getElementById('cart-items');
  const subtotalEl = document.getElementById('cart-subtotal');
  if (!list || !subtotalEl) return;

  const cart = getCart();
  list.innerHTML = '';

  if (!cart.length) {
    list.innerHTML = '<p>Your cart is waiting to be filled with gold.</p>';
    subtotalEl.textContent = '₹0';
    return;
  }

  let subtotal = 0;
  cart.forEach((item) => {
    subtotal += item.price * item.qty;
    const row = document.createElement('div');
    row.className = 'cart-item';
    row.innerHTML = `
      <div>
        <strong>${item.product}</strong>
        <p style="color: var(--gray-300); font-size: 0.9rem;">Grade I · Hand-harvested</p>
      </div>
      <div>Qty: ${item.qty}</div>
      <div>
        <strong>₹${item.price * item.qty}</strong>
        <button class="secondary-btn" style="margin-top: 0.5rem" data-remove="${item.product}">Remove</button>
      </div>
    `;
    list.appendChild(row);
  });

  subtotalEl.textContent = `₹${subtotal}`;

  list.querySelectorAll('[data-remove]').forEach((btn) =>
    btn.addEventListener('click', () => removeFromCart(btn.dataset.remove))
  );
};

const renderCheckoutSummary = () => {
  const summary = document.getElementById('checkout-summary');
  const subtotalEl = document.getElementById('checkout-subtotal');
  const shippingCostEl = document.getElementById('shipping-cost');
  const shippingLine = document.getElementById('shipping-line');
  const totalEl = document.getElementById('checkout-total');
  if (!summary || !totalEl) return;

  const cart = getCart();
  summary.innerHTML = '';
  let subtotal = 0;

  if (!cart.length) {
    summary.innerHTML = '<p>Your cart is empty.</p>';
    if (subtotalEl) subtotalEl.textContent = '₹0';
    if (shippingCostEl) shippingCostEl.textContent = '₹0';
    if (shippingLine) shippingLine.style.display = 'none';
    totalEl.textContent = '₹0';
    return;
  }

  cart.forEach((item) => {
    subtotal += item.price * item.qty;
    const itemDiv = document.createElement('div');
    itemDiv.className = 'summary-item';
    itemDiv.innerHTML = `
      <span class="summary-item-name">${item.product} × ${item.qty}</span>
      <span class="summary-item-price">₹${(item.price * item.qty).toLocaleString('en-IN')}</span>
    `;
    summary.appendChild(itemDiv);
  });

  // Calculate shipping cost
  const shippingMethod = document.querySelector('input[name="shipping"]:checked');
  const shippingCost = shippingMethod && shippingMethod.value === 'express' ? 299 : 0;

  if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toLocaleString('en-IN')}`;
  
  if (shippingCost > 0) {
    if (shippingCostEl) shippingCostEl.textContent = `₹${shippingCost.toLocaleString('en-IN')}`;
    if (shippingLine) shippingLine.style.display = 'flex';
  } else {
    if (shippingLine) shippingLine.style.display = 'none';
  }

  const total = subtotal + shippingCost;
  totalEl.textContent = `₹${total.toLocaleString('en-IN')}`;
};

const initCheckoutShipping = () => {
  const shippingInputs = document.querySelectorAll('input[name="shipping"]');
  if (!shippingInputs.length) return;
  shippingInputs.forEach((input) => {
    input.addEventListener('change', renderCheckoutSummary);
  });
};

const attachAddToCart = () => {
  document.querySelectorAll('[data-product]').forEach((btn) => {
    btn.addEventListener('click', () => addToCart(btn.dataset.product, btn.dataset.price));
  });
};

const handleSocialLogin = () => {
  const providerMap = {
    google: 'https://accounts.google.com/o/oauth2/v2/auth',
    apple: 'https://appleid.apple.com/auth/authorize',
  };

  document.querySelectorAll('.social-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const provider = btn.dataset.provider;
      const url = providerMap[provider];
      if (!url) return;
      window.open(url, '_blank', 'noopener');
    });
  });
};

const closeMoreMenus = () => {
  document.querySelectorAll('.nav-more.open').forEach((menu) => menu.classList.remove('open'));
};

const initMoreMenu = () => {
  const containers = document.querySelectorAll('.nav-more');
  if (!containers.length) return;

  containers.forEach((container) => {
    const toggle = container.querySelector('.nav-more-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = container.classList.contains('open');
      closeMoreMenus();
      container.classList.toggle('open', !isOpen);
    });
  });

  document.addEventListener('click', closeMoreMenus);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMoreMenus();
    }
  });
};

const initCheckoutForm = () => {
  const form = document.getElementById('checkout-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const cart = getCart();
    if (!cart.length) {
      alert('Your cart is empty. Please add items before checking out.');
      return;
    }

    const formData = new FormData(form);
    const fullName = formData.get('fullName')?.trim();
    const email = formData.get('email')?.trim();
    const phone = formData.get('phone')?.trim();
    const shippingMethod = formData.get('shipping');
    const paymentMethod = formData.get('payment');
    const notes = formData.get('notes')?.trim() || '';
    const address = {
      country: formData.get('country')?.trim(),
      line1: formData.get('address')?.trim(),
      line2: formData.get('address2')?.trim(),
      city: formData.get('city')?.trim(),
      postalCode: formData.get('zip')?.trim(),
    };

    if (!fullName || !email || !phone || !shippingMethod || !paymentMethod) {
      alert('Please fill out all required fields.');
      return;
    }

    const paymentValidation = validatePaymentDetails(paymentMethod, formData);
    if (!paymentValidation.valid) {
      alert(paymentValidation.message);
      return;
    }

    let subtotal = 0;
    cart.forEach((item) => {
      subtotal += item.price * item.qty;
    });

    const shippingCost = shippingMethod === 'express' ? 299 : 0;
    const total = subtotal + shippingCost;

    const order = {
      id: generateOrderId(),
      date: new Date().toISOString(),
      fullName,
      email,
      phone,
      shippingMethod,
      paymentMethod,
      shippingCost,
      subtotal,
      total,
      notes,
      address,
      items: cart,
      paymentStatus: paymentMethod === 'cod' ? 'Pending - Cash on Delivery' : 'Pending Confirmation',
    };

    try {
      await postJSON('/api/orders', {
        fullName,
        email,
        phone,
        shippingMethod,
        paymentMethod,
        shippingCost,
        subtotal,
        total,
        notes,
        address,
        items: cart,
        paymentStatus: order.paymentStatus,
      });
    } catch (err) {
      alert(err.message || 'Could not save order. Please log in and try again.');
      return;
    }

    saveOrderForEmail(email, order);
    saveCart([]);
    renderCart();
    renderCheckoutSummary();
    showReceiptModal(order);
    form.reset();

    const defaultShipping = document.querySelector('input[name="shipping"][value="standard"]');
    if (defaultShipping) defaultShipping.checked = true;
    const defaultPayment = document.querySelector('input[name="payment"][value="card"]');
    if (defaultPayment) defaultPayment.checked = true;
    togglePaymentDetails();
    renderCheckoutSummary();
  });
};

const validatePaymentDetails = (method, formData) => {
  if (method === 'upi') {
    const upiId = formData.get('upiId')?.trim();
    if (!upiId) {
      return { valid: false, message: 'Please enter your UPI ID.' };
    }
    const upiPattern = /^[\w.\-]{2,}@[a-zA-Z]{2,}$/;
    if (!upiPattern.test(upiId)) {
      return { valid: false, message: 'Please enter a valid UPI ID (example: name@bank).' };
    }
  }

  if (method === 'card') {
    const number = formData.get('cardNumber')?.replace(/\s+/g, '');
    const name = formData.get('cardName')?.trim();
    const expiry = formData.get('cardExpiry')?.trim();
    const cvv = formData.get('cardCvv')?.trim();

    if (!number || number.length < 12) {
      return { valid: false, message: 'Please enter a valid card number.' };
    }
    if (!name) {
      return { valid: false, message: 'Please enter the name on card.' };
    }
    if (!expiry || !/^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry)) {
      return { valid: false, message: 'Please enter a valid expiry date (MM/YY).' };
    }
    if (!cvv || cvv.length < 3) {
      return { valid: false, message: 'Please enter a valid CVV.' };
    }
  }

  return { valid: true };
};

const togglePaymentDetails = () => {
  const payment = document.querySelector('input[name="payment"]:checked')?.value;
  const cardFields = document.getElementById('card-fields');
  const upiFields = document.getElementById('upi-fields');
  const upiInput = document.querySelector('input[name="upiId"]');
  const cardInputs = document.querySelectorAll('#card-fields input');

  if (cardFields) {
    cardFields.classList.toggle('active', payment === 'card');
    cardInputs.forEach((input) => {
      input.required = payment === 'card';
    });
  }

  if (upiFields && upiInput) {
    const showUpi = payment === 'upi';
    upiFields.classList.toggle('active', showUpi);
    upiInput.required = showUpi;
  }

  if (payment === 'cod') {
    if (cardFields) cardFields.classList.remove('active');
    if (upiFields) upiFields.classList.remove('active');
    if (upiInput) upiInput.required = false;
    cardInputs.forEach((input) => {
      input.required = false;
    });
  }
};

const initPaymentDetails = () => {
  const paymentInputs = document.querySelectorAll('input[name="payment"]');
  if (!paymentInputs.length) return;
  paymentInputs.forEach((input) => input.addEventListener('change', togglePaymentDetails));
  togglePaymentDetails();
};

const setFormStatus = (el, type, message) => {
  if (!el) return;
  el.textContent = message;
  el.classList.remove('success', 'error');
  if (type) {
    el.classList.add(type);
  }
};

// OTP Verification Functions
const showOTPVerificationModal = (email) => {
  const modal = document.getElementById('otp-modal');
  const emailInput = document.getElementById('otp-email');
  const otpInput = document.getElementById('otp-code');
  const statusDiv = document.getElementById('otp-status');
  
  emailInput.value = email;
  otpInput.value = '';
  statusDiv.textContent = '';
  statusDiv.className = 'form-status';
  
  modal.style.display = 'flex';
  otpInput.focus();
};

const closeOTPModal = () => {
  const modal = document.getElementById('otp-modal');
  modal.style.display = 'none';
};

const verifyOTP = async () => {
  const email = document.getElementById('otp-email').value;
  const otp = document.getElementById('otp-code').value;
  const statusDiv = document.getElementById('otp-status');
  
  if (!email || !otp) {
    setFormStatus(statusDiv, 'error', 'Please enter the OTP code.');
    return;
  }
  
  if (otp.length !== 6 || !/^\d+$/.test(otp)) {
    setFormStatus(statusDiv, 'error', 'Please enter a valid 6-digit OTP.');
    return;
  }
  
  setFormStatus(statusDiv, null, 'Verifying...');
  
  try {
    await postJSON('/api/verify-otp', { email, otp });
    setFormStatus(statusDiv, 'success', 'Email verified successfully! You can now login.');
    
    // Close modal after success
    setTimeout(() => {
      closeOTPModal();
      // Switch to login tab
      const loginTab = document.querySelector('[data-tab="login"]');
      if (loginTab) loginTab.click();
    }, 2000);
    
  } catch (err) {
    setFormStatus(statusDiv, 'error', err.message);
  }
};

const resendOTP = async () => {
  const email = document.getElementById('otp-email').value;
  const statusDiv = document.getElementById('otp-status');
  
  setFormStatus(statusDiv, null, 'Resending OTP...');
  
  try {
    await postJSON('/api/resend-otp', { email });
    setFormStatus(statusDiv, 'success', 'OTP has been resent to your email.');
  } catch (err) {
    setFormStatus(statusDiv, 'error', err.message);
  }
};

// Auto-format phone and OTP inputs
document.addEventListener('DOMContentLoaded', () => {
  // Phone number formatting
  const phoneInputs = document.querySelectorAll('input[name="phone"]');
  phoneInputs.forEach(input => {
    input.addEventListener('input', (e) => {
      // Only allow digits, max 10
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10);
    });
  });

  // OTP input formatting
  const otpInput = document.getElementById('otp-code');
  if (otpInput) {
    otpInput.addEventListener('input', (e) => {
      // Only allow digits
      e.target.value = e.target.value.replace(/\D/g, '');
    });
    
    otpInput.addEventListener('keypress', (e) => {
      // Submit on Enter
      if (e.key === 'Enter') {
        verifyOTP();
      }
    });
  }
});

const handleAuthForms = () => {
  const registerForm = document.getElementById('register-form');
  const registerStatus = document.getElementById('register-status');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(registerForm);
      const fullName = formData.get('fullName')?.trim();
      const email = formData.get('email')?.trim();
      const phone = formData.get('phone')?.trim();
      const password = formData.get('password');
      const confirmPassword = formData.get('confirmPassword');

      // Client-side validation
      if (password !== confirmPassword) {
        setFormStatus(registerStatus, 'error', 'Passwords do not match.');
        return;
      }

      // Password strength validation
      if (password.length < 8) {
        setFormStatus(registerStatus, 'error', 'Password must be at least 8 characters long.');
        return;
      }

      if (!/[A-Z]/.test(password)) {
        setFormStatus(registerStatus, 'error', 'Password must contain at least one uppercase letter.');
        return;
      }

      if (!/[a-z]/.test(password)) {
        setFormStatus(registerStatus, 'error', 'Password must contain at least one lowercase letter.');
        return;
      }

      if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        setFormStatus(registerStatus, 'error', 'Password must contain at least one special character.');
        return;
      }

      // Phone number validation
      const cleanPhone = phone.replace(/\D/g, '');
      if (cleanPhone.length !== 10) {
        setFormStatus(registerStatus, 'error', 'Phone number must be exactly 10 digits.');
        return;
      }

      setFormStatus(registerStatus, null, 'Creating your account...');
      try {
        const response = await postJSON('/api/register', {
          full_name: fullName,
          email,
          phone,
          password,
        });
        
        // Show OTP verification modal
        showOTPVerificationModal(email);
        setFormStatus(registerStatus, 'success', 'Registration successful! Please check your email for OTP.');
        registerForm.reset();
      } catch (err) {
        setFormStatus(registerStatus, 'error', err.message);
      }
    });
  }

  const loginForm = document.getElementById('login-form');
  const loginStatus = document.getElementById('login-status');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(loginForm);
      const email = formData.get('email')?.trim();
      const password = formData.get('password');

      setFormStatus(loginStatus, null, 'Signing you in...');
      try {
        const response = await postJSON('/api/login', { email, password });
        setFormStatus(loginStatus, 'success', response.message || 'Login successful! Redirecting...');
        
        // Check if admin redirect is needed
        if (response.redirect === 'admin') {
          setTimeout(() => {
            window.location.href = 'SaffronIndiaAdmin/index.html';
          }, 1200);
        } else {
          setTimeout(() => {
            window.location.href = 'dashboard.html';
          }, 1200);
        }
      } catch (err) {
        setFormStatus(loginStatus, 'error', err.message);
      }
    });
  }
};

const loadUserInfo = async () => {
  try {
    const data = await getJSON('/api/user');
    if (data.success && data.user) {
      toggleAuthNav(true);
      const userName = document.getElementById('user-name');
      if (userName) {
        userName.textContent = data.user.full_name;
      }
      const adminLink = document.getElementById('admin-link');
      if (adminLink) {
        if (data.user.role === 'admin') {
          adminLink.classList.remove('hidden');
        } else {
          adminLink.classList.add('hidden');
        }
      }
      
      // Profile page
      const profileName = document.getElementById('profile-name');
      const profileEmail = document.getElementById('profile-email');
      const profilePhone = document.getElementById('profile-phone');
      const profileJoined = document.getElementById('profile-joined');
      
      if (profileName) profileName.textContent = data.user.full_name;
      if (profileEmail) profileEmail.textContent = data.user.email;
      if (profilePhone) profilePhone.textContent = data.user.phone || 'Not provided';
      if (profileJoined && data.user.created_at) {
        const date = new Date(data.user.created_at);
        profileJoined.textContent = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
      }

      renderOrderHistory(data.user);
    } else {
      toggleAuthNav(false);
    }
  } catch (err) {
    // Handle 401 Unauthorized - user not logged in
    if (err.message.includes('401') || err.message.includes('Unauthorized')) {
      console.log('User not authenticated, showing login/register');
      toggleAuthNav(false);
    } else {
      console.error('Error loading user info:', err);
      toggleAuthNav(false);
    }
    
    if (window.location.pathname.includes('dashboard.html') || window.location.pathname.includes('profile.html')) {
      window.location.href = 'login.html';
    }
  }
};

const handleLogout = async () => {
  try {
    await postJSON('/api/logout', {});
    window.location.href = 'index.html';
  } catch (err) {
    // Even if logout fails, clear local storage and redirect
    localStorage.removeItem('saffronindia-cart');
    window.location.href = 'index.html';
  }
};

const initLogout = () => {
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
};

const toggleAuthNav = (isLoggedIn) => {
  const authNav = document.getElementById('auth-nav');
  const userNav = document.getElementById('user-nav');
  const navMore = document.querySelector('.nav-more');
  
  if (isLoggedIn) {
    if (authNav) authNav.classList.add('hidden');
    if (userNav) userNav.style.display = 'flex';
    if (navMore) navMore.classList.add('visible');
  } else {
    if (authNav) authNav.classList.remove('hidden');
    if (userNav) userNav.style.display = 'none';
    if (navMore) navMore.classList.remove('visible');
  }
  
  // Show/hide Add to Cart buttons based on login status
  toggleAddToCartButtons(isLoggedIn);
};

const toggleAddToCartButtons = (isLoggedIn) => {
  const addToCartBtns = document.querySelectorAll('.add-to-cart-btn');
  addToCartBtns.forEach((btn) => {
    if (isLoggedIn) {
      btn.classList.add('visible');
    } else {
      btn.classList.remove('visible');
    }
  });
};

async function renderOrderHistory(user) {
  const historyEl = document.getElementById('order-history');
  if (!historyEl || !user) return;

  try {
    const data = await getJSON('/api/orders');
    const orders = data.orders || [];
    if (!orders.length) {
      historyEl.innerHTML = '<p style="color: var(--gray-300);">No orders yet. Your purchases will appear here.</p>';
      return;
    }

    historyEl.innerHTML = orders
      .map(
        (order) => `
          <div class="order-card">
            <div class="order-card-header">
              <strong>SI-${String(order.id).padStart(6, '0')}</strong>
              <span>${new Date(order.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
            </div>
            <div>
              <p class="receipt-label" style="margin-bottom: 0.35rem;">Items</p>
              <ul>
                ${(order.items || [])
                  .map((item) => `<li>${item.product_name} × ${item.qty}</li>`)
                  .join('')}
              </ul>
            </div>
            <p class="order-card-total">Total Paid: ₹${order.total.toLocaleString('en-IN')}</p>
            <p style="color: var(--gray-300); font-size: 0.85rem; margin-top: 0.5rem;">Status: ${order.status}</p>
          </div>
        `
      )
      .join('');
  } catch (err) {
    historyEl.innerHTML = '<p style="color: var(--gray-300);">Unable to load orders right now.</p>';
  }
}

function populateReceiptModal(order) {
  const receiptId = document.getElementById('receipt-id');
  const receiptName = document.getElementById('receipt-name');
  const receiptEmail = document.getElementById('receipt-email');
  const receiptDate = document.getElementById('receipt-date');
  const receiptItems = document.getElementById('receipt-items');
  const receiptSubtotal = document.getElementById('receipt-subtotal');
  const receiptShipping = document.getElementById('receipt-shipping');
  const receiptShippingLine = document.getElementById('receipt-shipping-line');
  const receiptTotal = document.getElementById('receipt-total');

  if (receiptId) receiptId.textContent = order.id;
  if (receiptName) receiptName.textContent = order.fullName || 'Valued Guest';
  if (receiptEmail) receiptEmail.textContent = order.email || '';
  if (receiptDate) {
    receiptDate.textContent = new Date(order.date).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  if (receiptItems) {
    receiptItems.innerHTML = order.items
      .map(
        (item) => `
          <div class="receipt-item">
            <span>${item.product} × ${item.qty}</span>
            <span>₹${(item.price * item.qty).toLocaleString('en-IN')}</span>
          </div>
        `
      )
      .join('');
  }

  if (receiptSubtotal) receiptSubtotal.textContent = `₹${order.subtotal.toLocaleString('en-IN')}`;
  if (receiptShipping) receiptShipping.textContent = `₹${order.shippingCost.toLocaleString('en-IN')}`;
  if (receiptShippingLine) receiptShippingLine.style.display = order.shippingCost > 0 ? 'flex' : 'none';
  if (receiptTotal) receiptTotal.textContent = `₹${order.total.toLocaleString('en-IN')}`;
}

function showReceiptModal(order) {
  const modal = document.getElementById('receipt-modal');
  if (!modal) return;
  currentReceiptOrder = order;
  populateReceiptModal(order);
  modal.classList.add('active');
  document.body.classList.add('modal-open');
}

function closeReceiptModal() {
  const modal = document.getElementById('receipt-modal');
  if (!modal) return;
  modal.classList.remove('active');
  document.body.classList.remove('modal-open');
}

function downloadReceipt() {
  if (!currentReceiptOrder) return;
  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert('PDF generator is still loading. Please try again.');
    return;
  }

  const order = currentReceiptOrder;
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const width = doc.internal.pageSize.getWidth();
  let y = 20;

  const addText = (text, options = {}) => {
    const { size = 12, style = 'normal', align = 'left', x = 20 } = options;
    doc.setFont('helvetica', style);
    doc.setFontSize(size);
    if (align === 'center') {
      doc.text(text, width / 2, y, { align: 'center' });
    } else {
      doc.text(text, x, y);
    }
    y += size * 0.5 + 4;
  };

  const addLine = () => {
    doc.setDrawColor(212, 175, 55);
    doc.setLineWidth(0.5);
    doc.line(20, y, width - 20, y);
    y += 6;
  };

  addText('SAFFRON INDIA', { size: 16, style: 'bold', align: 'center' });
  addText('Order Receipt', { size: 12, align: 'center' });
  y += 4;
  addLine();

  addText(`Order ID: ${order.id}`, { style: 'bold' });
  addText(`Date: ${new Date(order.date).toLocaleString('en-IN')}`);
  addText(`Customer: ${order.fullName}`);
  addText(`Email: ${order.email}`);
  addText(`Phone: ${order.phone}`);
  y += 2;
  addLine();

  addText('Items', { style: 'bold' });
  order.items.forEach((item) => {
    const lineText = `${item.product} × ${item.qty}`;
    const priceText = `₹${(item.price * item.qty).toLocaleString('en-IN')}`;
    doc.text(lineText, 20, y);
    doc.text(priceText, width - 20, y, { align: 'right' });
    y += 8;
    if (y > 270) {
      doc.addPage();
      y = 20;
    }
  });

  y += 4;
  addLine();
  addText(`Subtotal: ₹${order.subtotal.toLocaleString('en-IN')}`, { style: 'bold' });
  if (order.shippingCost > 0) {
    addText(`Shipping: ₹${order.shippingCost.toLocaleString('en-IN')}`, { style: 'bold' });
  }
  addText(`Total Paid: ₹${order.total.toLocaleString('en-IN')}`, { style: 'bold' });
  addLine();
  addText('Thank you for supporting artisan saffron growers.', { size: 10, align: 'center' });

  doc.save(`${order.id}_receipt.pdf`);
}

function initReceiptModal() {
  const modal = document.getElementById('receipt-modal');
  if (!modal) return;
  const closeBtn = document.getElementById('receipt-close');
  const doneBtn = document.getElementById('receipt-done');
  const downloadBtn = document.getElementById('receipt-download');

  if (closeBtn) closeBtn.addEventListener('click', closeReceiptModal);
  if (doneBtn) doneBtn.addEventListener('click', closeReceiptModal);
  if (downloadBtn) downloadBtn.addEventListener('click', downloadReceipt);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeReceiptModal();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
      closeReceiptModal();
    }
  });
};

const updateYear = () => {
  const yearEls = document.querySelectorAll('#year');
  yearEls.forEach((el) => (el.textContent = new Date().getFullYear()));
};

// Dynamic product rendering - Append admin products to existing products
const renderProductsFromAPI = async () => {
  try {
    const data = await getJSON('/api/products');
    const products = data.products || [];
    
    if (products.length === 0) {
      console.log('No products found in API');
      return;
    }
    
    // Find the admin products container and append products there
    const adminContainer = document.getElementById('admin-products-container');
    if (adminContainer) {
      appendAdminProducts(adminContainer, products);
    }
  } catch (err) {
    // Handle different error types
    if (err.message.includes('401') || err.message.includes('Unauthorized')) {
      console.log('Products API requires authentication - user not logged in');
    } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
      console.error('Server error when fetching products - backend may be down:', err);
    } else if (err.message.includes('404') || err.message.includes('Not Found')) {
      console.log('Products API endpoint not found - using static products only');
    } else {
      console.error('Error fetching products:', err);
    }
    
    // Silently fail - the page will still work with static products
    console.log('Continuing with static products only');
  }
};

const appendAdminProducts = (container, products) => {
  if (!products || products.length === 0) return;
  
  const isLoggedIn = document.getElementById('auth-nav') && document.getElementById('auth-nav').classList.contains('hidden');
  
  const productsHTML = products.map((product, index) => `
    <article class="product-card" style="animation-delay: ${(index + 3) * 0.1}s">
      <span class="badge">${product.active ? 'Available' : 'Unavailable'}</span>
      <img src="${product.image_url || 'https://via.placeholder.com/300'}" alt="${product.name}" />
      <h3 class="product-title">${product.name}</h3>
      <p>${product.description || 'Premium saffron product'}</p>
      <div class="product-meta">
        <span class="price">&#8377;${product.price}</span>
        <div class="product-actions">
          <button class="primary-btn add-to-cart-btn ${isLoggedIn ? 'visible' : ''}" data-product="${product.name}" data-price="${product.price}">Add to Cart</button>
          <button class="learn-more-link" onclick="showProductDetails('${product.name}', '${product.description || 'Premium saffron product'}', '${product.price}')">Learn More</button>
        </div>
      </div>
    </article>
  `).join('');
  
  container.innerHTML = productsHTML;
  
  // Re-attach event listeners for Add to Cart buttons
  attachAddToCart();
};

// Product Details Modal Functions
let currentProductData = null;

const showProductDetails = (productName, description, price) => {
  currentProductData = { productName, price };
  const modal = document.getElementById('product-details-modal');
  const titleEl = document.getElementById('product-details-title');
  const descEl = document.getElementById('product-details-description');
  const priceEl = document.getElementById('product-details-price');
  const addBtn = document.getElementById('product-details-add-btn');
  
  if (titleEl) titleEl.textContent = productName;
  if (descEl) descEl.textContent = description;
  if (priceEl) priceEl.textContent = `₹${price}`;
  
  // Check if user is logged in and show/hide Add to Cart button
  const authNav = document.getElementById('auth-nav');
  const isLoggedIn = authNav && authNav.classList.contains('hidden');
  
  if (addBtn) {
    if (isLoggedIn) {
      addBtn.style.display = 'inline-flex';
    } else {
      addBtn.style.display = 'none';
    }
  }
  
  if (modal) {
    modal.style.display = 'flex';
    document.body.classList.add('modal-open');
  }
};

const closeProductDetails = () => {
  const modal = document.getElementById('product-details-modal');
  if (modal) {
    modal.style.display = 'none';
    document.body.classList.remove('modal-open');
  }
};

const addProductFromModal = () => {
  if (currentProductData) {
    addToCart(currentProductData.productName, currentProductData.price);
    closeProductDetails();
  }
};

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('product-details-modal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeProductDetails();
      }
    });
    
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display === 'flex') {
        closeProductDetails();
      }
    });
  }
});

document.addEventListener('DOMContentLoaded', () => {
  attachAddToCart();
  renderCart();
  renderCheckoutSummary();
  initCheckoutForm();
  initCheckoutShipping();
  initPaymentDetails();
  updateYear();
  handleSocialLogin();
  initMoreMenu();
  handleAuthForms();
  loadUserInfo();
  initLogout();
  renderProductsFromAPI();
  initReceiptModal();
});

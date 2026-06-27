// ══════════════════════════════════════════════
//  KisanMitra — Main JS
// ══════════════════════════════════════════════

// Navbar scroll effect
const nav = document.getElementById('mainNav');
if (nav) {
    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 20);
    });
}

// Mobile nav toggle
const toggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');
if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
        navLinks.classList.toggle('open');
        toggle.classList.toggle('open');
    });
}

// Fade in on scroll
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) { e.target.style.opacity = '1'; e.target.style.transform = 'translateY(0)'; }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .module-card, .team-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity .6s ease, transform .6s ease';
    observer.observe(el);
});

// Accordion
document.querySelectorAll('.accordion-header').forEach(header => {
    header.addEventListener('click', () => {
        const item = header.parentElement;
        const isOpen = item.classList.contains('open');
        document.querySelectorAll('.accordion-item').forEach(i => i.classList.remove('open'));
        if (!isOpen) item.classList.add('open');
    });
});

// Star Rating
document.querySelectorAll('.star-btn').forEach((star, i, stars) => {
    star.addEventListener('click', () => {
        const val = parseInt(star.dataset.val);
        document.getElementById('ratingInput').value = val;
        stars.forEach((s, j) => s.classList.toggle('active', j < val));
    });
    star.addEventListener('mouseover', () => {
        const val = parseInt(star.dataset.val);
        stars.forEach((s, j) => s.classList.toggle('active', j < val));
    });
});

// Image upload preview
const uploadInput = document.getElementById('imageUpload');
const previewContainer = document.getElementById('previewContainer');
const previewImg = document.getElementById('previewImg');
const uploadZone = document.getElementById('uploadZone');

if (uploadInput) {
    uploadInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = e => {
                previewImg.src = e.target.result;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(this.files[0]);
        }
    });

    // Drag and drop
    if (uploadZone) {
        ['dragenter','dragover'].forEach(e => uploadZone.addEventListener(e, ev => {
            ev.preventDefault(); uploadZone.classList.add('dragging');
        }));
        ['dragleave','drop'].forEach(e => uploadZone.addEventListener(e, ev => {
            ev.preventDefault(); uploadZone.classList.remove('dragging');
        }));
        uploadZone.addEventListener('drop', ev => {
            const file = ev.dataTransfer.files[0];
            if (file) {
                const dt = new DataTransfer();
                dt.items.add(file);
                uploadInput.files = dt.files;
                const reader = new FileReader();
                reader.onload = e => {
                    previewImg.src = e.target.result;
                    previewContainer.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

// Animate confidence bar
const bar = document.getElementById('confidenceBar');
if (bar) {
    const target = bar.dataset.confidence;
    setTimeout(() => { bar.style.width = target + '%'; }, 300);
}

// Counter animation
function animateCounter(el) {
    const target = parseInt(el.dataset.target);
    let count = 0;
    const step = Math.ceil(target / 80);
    const timer = setInterval(() => {
        count = Math.min(count + step, target);
        el.textContent = count.toLocaleString();
        if (count >= target) clearInterval(timer);
    }, 16);
}
document.querySelectorAll('[data-target]').forEach(el => {
    const obs = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) { animateCounter(el); obs.disconnect(); }
    });
    obs.observe(el);
});

// Disease Library Filter
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        const filter = this.dataset.filter;
        document.querySelectorAll('.accordion-item').forEach(item => {
            item.style.display = (filter === 'all' || item.dataset.module === filter) ? 'block' : 'none';
        });
    });
});

// Weather widget
const weatherForm = document.getElementById('weatherForm');
if (weatherForm) {
    weatherForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const city = document.getElementById('cityInput').value.trim();
        if (!city) return;

        const mockWeather = {
            'Mumbai': { temp: 31, icon: '⛅', desc: 'Partly Cloudy', humidity: 78, wind: 18, uv: 7 },
            'Pune': { temp: 28, icon: '☀️', desc: 'Sunny', humidity: 55, wind: 12, uv: 8 },
            'Delhi': { temp: 38, icon: '🌤', desc: 'Hot & Hazy', humidity: 42, wind: 8, uv: 9 },
            'Nagpur': { temp: 36, icon: '☀️', desc: 'Clear Sky', humidity: 38, wind: 14, uv: 10 },
            'Nashik': { temp: 27, icon: '🌥', desc: 'Cloudy', humidity: 65, wind: 16, uv: 6 },
        };
        const w = mockWeather[city] || { temp: Math.round(25+Math.random()*15), icon: '🌤', desc: 'Partly Cloudy', humidity: Math.round(40+Math.random()*40), wind: Math.round(8+Math.random()*20), uv: Math.round(5+Math.random()*6) };

        document.getElementById('wIcon').textContent = w.icon;
        document.getElementById('wTemp').textContent = w.temp + '°C';
        document.getElementById('wCity').textContent = city;
        document.getElementById('wDesc').textContent = w.desc;
        document.getElementById('wHumidity').textContent = w.humidity + '%';
        document.getElementById('wWind').textContent = w.wind + ' km/h';
        document.getElementById('wUV').textContent = w.uv;
        document.getElementById('weatherResult').style.display = 'block';

        // Advisory
        let adv = '';
        if (w.humidity > 70) adv = '⚠️ High humidity: Risk of fungal diseases. Apply preventive fungicide.';
        else if (w.temp > 35) adv = '🌡️ High temperature: Ensure adequate irrigation and shade for sensitive crops.';
        else adv = '✅ Favorable weather conditions for crop growth.';
        document.getElementById('weatherAdvisory').textContent = adv;
    });
}

// Chatbot toggle (basic)
const chatBtn = document.getElementById('chatbotBtn');
const chatBox = document.getElementById('chatbox');
if (chatBtn && chatBox) {
    chatBtn.addEventListener('click', () => chatBox.classList.toggle('open'));
}

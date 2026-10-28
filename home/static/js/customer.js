  const $ = s => document.querySelector(s);
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const URLS = { send: "{% url 'send_otp' %}", verify: "{% url 'verify_otp' %}" };
  const boxes = [...document.querySelectorAll('#otpBoxes input')];
  let phone = "", timerId = null;

  function show(id){
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    $(id).classList.add('active');
  }
  function msg(el, text, ok=false){ el.textContent = text; el.classList.toggle('ok', ok); }
  function loading(btn, on){ btn.classList.toggle('loading', on); btn.disabled = on; }
  async function post(url, data){
    try{
      const r = await fetch(url, {
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRFToken':csrf},
        body: JSON.stringify(data)
      });
      return await r.json();
    }catch(e){ return {ok:false, error:'Network error. Check your connection.'}; }
  }
  const getOtp = () => boxes.map(b => b.value).join('');

  function startTimer(sec){
    clearInterval(timerId);
    const btn = $('#resendBtn'), t = $('#timer');
    btn.disabled = true; t.textContent = `(${sec}s)`;
    timerId = setInterval(() => {
      sec--;
      if(sec <= 0){ clearInterval(timerId); t.textContent = ''; btn.disabled = false; }
      else t.textContent = `(${sec}s)`;
    }, 1000);
  }

  // digits only in phone box
  $('#phone').addEventListener('input', e => {
    e.target.value = e.target.value.replace(/\D/g,'').slice(0,10);
    msg($('#phoneErr'), '');
  });

  // STEP 1 – send OTP
  $('#phoneForm').addEventListener('submit', async e => {
    e.preventDefault();
    const val = $('#phone').value;
    if(!/^[6-9]\d{9}$/.test(val)){ msg($('#phoneErr'), 'Enter a valid 10-digit mobile number.'); return; }
    loading($('#sendBtn'), true);
    const res = await post(URLS.send, {phone: val});
    loading($('#sendBtn'), false);
    if(!res.ok){ msg($('#phoneErr'), res.error); return; }
    phone = val;
    $('#shownPhone').textContent = '+91 ' + val.slice(0,2) + '••••••' + val.slice(-2);
    boxes.forEach(b => b.value = '');
    msg($('#otpErr'), '');
    show('#otpForm');
    startTimer(res.resend_in || 30);
    boxes[0].focus();
  });

  // OTP boxes behaviour
  boxes.forEach((b, i) => {
    b.addEventListener('input', () => {
      b.value = b.value.replace(/\D/g,'').slice(-1);
      msg($('#otpErr'), '');
      if(b.value && i < 5) boxes[i+1].focus();
      if(getOtp().length === 6) $('#otpForm').requestSubmit();
    });
    b.addEventListener('keydown', e => {
      if(e.key === 'Backspace' && !b.value && i > 0) boxes[i-1].focus();
      if(e.key === 'ArrowLeft' && i > 0) boxes[i-1].focus();
      if(e.key === 'ArrowRight' && i < 5) boxes[i+1].focus();
    });
    b.addEventListener('paste', e => {
      e.preventDefault();
      const t = (e.clipboardData.getData('text') || '').replace(/\D/g,'').slice(0,6);
      t.split('').forEach((c, k) => boxes[k].value = c);
      boxes[Math.min(t.length, 5)].focus();
      if(t.length === 6) $('#otpForm').requestSubmit();
    });
  });

  // STEP 2 – verify
  $('#otpForm').addEventListener('submit', async e => {
    e.preventDefault();
    const otp = getOtp();
    if(otp.length < 6){ msg($('#otpErr'), 'Enter the 6-digit OTP.'); return; }
    loading($('#verifyBtn'), true);
    const res = await post(URLS.verify, {phone, otp});
    loading($('#verifyBtn'), false);
    if(!res.ok){
      msg($('#otpErr'), res.error);
      const wrap = $('#otpBoxes');
      wrap.classList.remove('shake'); void wrap.offsetWidth; wrap.classList.add('shake');
      boxes.forEach(b => b.value = ''); boxes[0].focus();
      return;
    }
    show('#success');
    setTimeout(() => location.href = res.redirect || '/dashboard/', 1300);
  });

  // resend
  $('#resendBtn').addEventListener('click', async () => {
    $('#resendBtn').disabled = true;
    const res = await post(URLS.send, {phone});
    if(!res.ok){ msg($('#otpErr'), res.error); if(res.wait) startTimer(res.wait); else $('#resendBtn').disabled = false; return; }
    boxes.forEach(b => b.value = ''); boxes[0].focus();
    msg($('#otpErr'), 'A new OTP has been sent ✔', true);
    startTimer(res.resend_in || 30);
  });

  $('#changeNum').addEventListener('click', () => { clearInterval(timerId); show('#phoneForm'); $('#phone').focus(); });
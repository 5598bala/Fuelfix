# Deploy FuelFix on PythonAnywhere

The repository is https://github.com/5598bala/Fuelfix.git. This project uses Django 6.1.1 and needs Python 3.12 or newer; choose Python 3.13 in PythonAnywhere if it is available for your account.

## 1. Get the code and install dependencies

Open a Bash console in PythonAnywhere:

~~~bash
cd ~
git clone https://github.com/5598bala/Fuelfix.git
cd Fuelfix
python3.13 -m venv ~/.virtualenvs/fuelfix
source ~/.virtualenvs/fuelfix/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

If the repository is already cloned, use cd ~/Fuelfix and git pull instead. If your account does not offer Python 3.13, choose Python 3.12 if it is listed; Django 6.1.1 requires Python 3.12 or newer. PythonAnywhere says available versions depend on your account system image, so switch to a newer image if your account only has older versions.

## 2. Create the private settings file

Copy .env.example to .env in the project root and edit it in the PythonAnywhere Files tab. Set:

- SECRET_KEY to a newly generated random value. In a Bash console, generate one with python -c "import secrets; print(secrets.token_urlsafe(64))".
- DEBUG=False
- ALLOWED_HOSTS to the exact hostname shown for your PythonAnywhere web app, with no scheme or path.
- CSRF_TRUSTED_ORIGINS to that same hostname with https:// in front.
- Your own Geoapify, MeraOTP, Gmail SMTP, and Razorpay credentials.

Keep .env private. It is ignored by Git. Use Razorpay test credentials while checking checkout and webhooks; only switch to live credentials after those checks succeed.

## 3. Create the PythonAnywhere web app

In the PythonAnywhere Web tab, add a web app using Manual Configuration and the same Python version as the virtualenv. Set its virtualenv to:

/home/YOUR_USERNAME/.virtualenvs/fuelfix

Set the source code and working directory to:

/home/YOUR_USERNAME/Fuelfix

Open the WSGI file linked from the Web tab and replace its contents with this, changing the username/path:

~~~python
import os
import sys

path = "/home/YOUR_USERNAME/Fuelfix"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Fuelfix.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
~~~

The project settings file loads the project-root .env before reading SECRET_KEY.

## 4. Initialize the database and static files

In a Bash console:

~~~bash
cd ~/Fuelfix
source ~/.virtualenvs/fuelfix/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
~~~

In the Web tab, add a Static Files mapping:

- URL: /static/
- Directory: /home/YOUR_USERNAME/Fuelfix/staticfiles

For uploaded media, add:

- URL: /media/
- Directory: /home/YOUR_USERNAME/Fuelfix/media

Then reload the web app.

## 5. Update third-party callback URLs and test

After the site is live, update the Google OAuth callback URL to (replace YOUR_SITE_HOSTNAME with the exact domain shown in the Web tab; account region can change the domain):

https://YOUR_SITE_HOSTNAME/accounts/google/login/callback/

If you use Razorpay webhooks, set the webhook URL to:

https://YOUR_SITE_HOSTNAME/payments/razorpay/webhook/

Test login, OTP delivery, a fuel request, provider tracking, email reset, and Razorpay test-mode checkout. Check the Web tab error log if the site does not load.

## PythonAnywhere free-account network limit

PythonAnywhere documents that free accounts can call only allowlisted external sites; paid accounts have unrestricted outbound internet. FuelFix calls external Geoapify, MeraOTP, Gmail, and Razorpay services, so check that each required API domain is reachable or allowlisted for your account before relying on those integrations.

Official references:
- https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/
- https://help.pythonanywhere.com/pages/DjangoStaticFiles/
- https://help.pythonanywhere.com/pages/PythonVersions/
- https://help.pythonanywhere.com/pages/403ForbiddenError/
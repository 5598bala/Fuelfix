# Deploy FuelFix on Render

Render reads `render.yaml` from this repository. The Blueprint creates a Django
web service and PostgreSQL database, collects static files with WhiteNoise, and
runs migrations on each deployment. The web service and database are set to
Render's free plans by default to avoid starting a paid service without your
approval.

## Connect and deploy

1. In Render, choose **New → Blueprint** and connect the FuelFix GitHub repo.
2. Review the `fuelfix` web service and `fuelfix-db` database. The initial
   blueprint screen asks for the MeraOTP, Geoapify, and Google OAuth secrets.
   Enter them directly in Render's secure fields; never commit them to Git.
3. Apply the Blueprint. Render assigns the app an `onrender.com` hostname and
   deploys it from `main` on future pushes.
4. In Google Cloud Console, add that exact HTTPS host as an authorized
   JavaScript origin, and add
   `https://<render-host>/accounts/google/login/callback/` as an authorized
   redirect URI for the same OAuth web client.
5. Test OTP using your own phone (MeraOTP may charge prepaid credit), Google
   sign-in, then provider GPS on an accepted job using a phone browser. Grant
   location access and keep the provider page open during the delivery.

## Render free-plan limits

Render's free web service sleeps after 15 minutes without traffic, so the next
visit can wait about a minute. Free Postgres expires 30 days after creation;
after its grace period Render deletes its data. Upgrade the database to a paid
plan before relying on it for durable customer accounts or requests. Render's
free web service also has an ephemeral filesystem, so uploaded media files are
not durable across restarts or deploys. Gmail SMTP password reset is not
available from free web services because outbound SMTP is blocked.

## Existing PythonAnywhere data

The Render database starts empty and is independent of PythonAnywhere. Existing
customer/provider accounts, fuel requests, admin records, and uploaded files
are not copied by this deployment. Keep the PythonAnywhere site available until
you decide whether to migrate its live database and media.

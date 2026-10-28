document.addEventListener("DOMContentLoaded", () => {
 const button=document.getElementById("mechanicGetLocation"); if(!button)return;
 const address=document.getElementById("mechanicAddress"), lat=document.getElementById("mechanicLatitude"), lon=document.getElementById("mechanicLongitude"), status=document.getElementById("mechanicLocationStatus");
 button.addEventListener("click",()=>{
  if(!navigator.geolocation){status.textContent="Location is not supported. Enter your address manually.";return;}
  status.textContent="Finding your location…";
  navigator.geolocation.getCurrentPosition(position=>{
   lat.value=position.coords.latitude; lon.value=position.coords.longitude;
   address.value=`GPS location (${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)})`;
   status.textContent="Location added. You can edit the address if needed.";
  },()=>{status.textContent="Could not get your location. Enter your address manually.";},{enableHighAccuracy:true,timeout:15000,maximumAge:5000});
 });
});

(() => {
 const page=document.getElementById("sosLivePage"); if(!page)return;
 const status=document.getElementById("sosLiveStatus"), coords=document.getElementById("sosLiveCoordinates"), updated=document.getElementById("sosLiveUpdated"), openMap=document.getElementById("sosOpenMap"), key=page.dataset.geoapifyKey;
 let map=null, marker=null;
 if(key&&window.L){
  map=L.map("sosLiveMap").setView([20.5937,78.9629],5);
  L.tileLayer(`https://maps.geoapify.com/v1/tile/osm-carto/{z}/{x}/{y}.png?apiKey=${encodeURIComponent(key)}`,{attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://www.geoapify.com/">Geoapify</a>',maxZoom:20}).addTo(map);
 }
 async function refresh(){
  try{
   const response=await fetch(page.dataset.locationUrl,{cache:"no-store"});
   if(!response.ok)throw new Error("This location link is invalid or has expired.");
   const data=await response.json();
   if(data.revoked){status.textContent="Location sharing was stopped by the customer.";coords.textContent="No longer shared";updated.textContent="—";openMap.hidden=true;if(map)map.remove();map=null;return;}
   const lat=Number(data.latitude), lon=Number(data.longitude);
   coords.textContent=`${lat.toFixed(6)}, ${lon.toFixed(6)}`; updated.textContent=new Date(data.updated_at).toLocaleString();
   openMap.href=`https://www.google.com/maps?q=${lat},${lon}`; openMap.hidden=false;
   if(map){if(!marker){marker=L.marker([lat,lon]).addTo(map);map.setView([lat,lon],16);}else{marker.setLatLng([lat,lon]);map.panTo([lat,lon]);}}
   status.textContent=data.active?"Live location is updating.":"Location is no longer updating. This is the last point received.";
  }catch(error){status.textContent=error.message||"Could not load the current location.";}
 }
 refresh(); window.setInterval(refresh,5000);
})();

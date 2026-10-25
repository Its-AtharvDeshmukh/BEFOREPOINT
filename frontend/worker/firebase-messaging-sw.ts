/// <reference lib="webworker" />
import {initializeApp,type FirebaseOptions} from 'firebase/app';
import {getMessaging,onBackgroundMessage} from 'firebase/messaging/sw';
declare const __FIREBASE_CONFIG__:FirebaseOptions;
const sw=self as unknown as ServiceWorkerGlobalScope;
sw.addEventListener('notificationclick',event=>{event.notification.close();const target=new URL(event.notification.data?.path||'/citizen',sw.location.origin);if(target.origin!==sw.location.origin)return;event.waitUntil(sw.clients.matchAll({type:'window',includeUncontrolled:true}).then(async clients=>{for(const client of clients){if('focus'in client){await client.navigate(target.href);return client.focus()}}return sw.clients.openWindow(target.href)}))});
if(__FIREBASE_CONFIG__.apiKey){const app=initializeApp(__FIREBASE_CONFIG__);onBackgroundMessage(getMessaging(app),payload=>{const data=payload.data||{};return sw.registration.showNotification(data.title||'BEFOREPOINT · Test only',{body:data.body||'A test observation request is available.',tag:'sentinel-test',data:{path:data.path||'/citizen'}})})}

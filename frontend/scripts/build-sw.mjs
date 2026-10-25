import {build} from 'esbuild';
import {loadEnv} from 'vite';
const env=loadEnv('production',process.cwd(),'VITE_');
const config={apiKey:env.VITE_FIREBASE_API_KEY||'',authDomain:env.VITE_FIREBASE_AUTH_DOMAIN||'',projectId:env.VITE_FIREBASE_PROJECT_ID||'',storageBucket:env.VITE_FIREBASE_STORAGE_BUCKET||'',messagingSenderId:env.VITE_FIREBASE_MESSAGING_SENDER_ID||'',appId:env.VITE_FIREBASE_APP_ID||''};
await build({entryPoints:['worker/firebase-messaging-sw.ts'],outfile:'public/firebase-messaging-sw.js',bundle:true,minify:true,format:'iife',target:'es2022',define:{__FIREBASE_CONFIG__:JSON.stringify(config)}});
console.log('Bundled messaging service worker.');

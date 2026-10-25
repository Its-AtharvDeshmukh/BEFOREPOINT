import {defineConfig} from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[tailwindcss()],worker:{format:'es'},server:{proxy:{'/api':'http://127.0.0.1:8000'}},build:{outDir:'dist',rollupOptions:{output:{manualChunks(id){if(id.includes('maplibre-gl'))return 'map';if(id.includes('@xyflow'))return 'graph';if(id.includes('recharts')||id.includes('d3-'))return 'charts';if(id.includes('@firebase')||id.includes('/firebase/'))return 'firebase';}}}}});

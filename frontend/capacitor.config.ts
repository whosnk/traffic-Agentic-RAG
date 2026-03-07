import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.asmile.traffic',
  appName: 'ITQA交通助手',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    cleartext: true // 允许 HTTP 访问
  }
};
export default config;
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  DeviceEventEmitter,
  StatusBar,
  ScrollView,
  TextInput,
  Alert,
  FlatList,
  Linking,
  Animated,
  Easing,
  Image,
  Dimensions,
  Platform,
  RefreshControl,
  ActivityIndicator,
  NativeModules,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  requestPermission,
  checkPermission,
  showFloatingBubble,
  hideFloatingBubble,
  initialize,
  reopenApp,
  setSlideshowImages,
} from 'react-native-floating-bubble';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const { HudBridge } = NativeModules;

// ═══════════════════════════════════════════════════════════
//  CONFIG - Update SERVER_IP to your laptop's local IP
// ═══════════════════════════════════════════════════════════
const SERVER_IP = ''; // Will be auto-detected or manually set
const SERVER_PORT = 8844;
const PAIR_CODE = ''; // Will be entered by user

const ACCENT = '#e62117';
const BG = '#050505';
const BG2 = '#0d0d0d';
const BG3 = '#121212';
const DIM = '#666666';
const TEXT = '#f0f0f0';
const RED = '#b31b14';
const GREEN = '#4caf50';

// ═══════════════════════════════════════════════════════════
//  ANIMATED GLOW TEXT
// ═══════════════════════════════════════════════════════════
function GlowText({ children, style }) {
  const anim = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 1, duration: 1200, useNativeDriver: false }),
        Animated.timing(anim, { toValue: 0.4, duration: 1200, useNativeDriver: false }),
      ])
    ).start();
  }, []);
  return (
    <Animated.Text style={[style, { opacity: anim }]}>
      {children}
    </Animated.Text>
  );
}

// ═══════════════════════════════════════════════════════════
//  ARC GAUGE COMPONENT
// ═══════════════════════════════════════════════════════════
function ArcGauge({ label, value, color, size = 100 }) {
  const percentage = Math.min(100, Math.max(0, value));
  const barWidth = (size - 24) * (percentage / 100);
  return (
    <View style={[gaugeStyles.container, { width: size }]}>
      <Text style={[gaugeStyles.value, { color }]}>{percentage.toFixed(0)}%</Text>
      <View style={gaugeStyles.barBg}>
        <View style={[gaugeStyles.barFill, { width: `${percentage}%`, backgroundColor: color }]} />
      </View>
      <Text style={gaugeStyles.label}>{label}</Text>
    </View>
  );
}
const gaugeStyles = StyleSheet.create({
  container: { alignItems: 'center', padding: 8 },
  value: { fontSize: 22, fontWeight: '900', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  barBg: { width: '100%', height: 6, backgroundColor: '#222', borderRadius: 3, marginTop: 4, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 3 },
  label: { color: DIM, fontSize: 9, fontWeight: 'bold', letterSpacing: 2, marginTop: 4, textTransform: 'uppercase' },
});

// ═══════════════════════════════════════════════════════════
//  FILE ICON HELPER
// ═══════════════════════════════════════════════════════════
function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  const icons = {
    pdf: '📄', doc: '📝', docx: '📝', txt: '📝',
    jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', webp: '🖼️', svg: '🖼️',
    mp4: '🎬', mkv: '🎬', avi: '🎬', mov: '🎬',
    mp3: '🎵', wav: '🎵', flac: '🎵', aac: '🎵',
    zip: '📦', rar: '📦', tar: '📦', gz: '📦',
    apk: '📱', exe: '💻', deb: '💻',
    py: '🐍', js: '⚡', html: '🌐', css: '🎨', json: '📋',
  };
  return icons[ext] || '📄';
}

// ═══════════════════════════════════════════════════════════
//  MAIN APP
// ═══════════════════════════════════════════════════════════
export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const introFade = useRef(new Animated.Value(1)).current;
  const introScale = useRef(new Animated.Value(0.2)).current;
  // Intro Logic
  useEffect(() => {
    // Start intro animation
    Animated.spring(introScale, {
      toValue: 1,
      friction: 6,
      tension: 40,
      useNativeDriver: true,
    }).start();

    const timer = setTimeout(() => {
      Animated.timing(introFade, {
        toValue: 0,
        duration: 1000,
        useNativeDriver: true,
      }).start(() => setShowIntro(false));
    }, 2800);

    return () => clearTimeout(timer);
  }, []);

  const [hasPermission, setHasPermission] = useState(false);
  const [isBubbleVisible, setIsBubbleVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [serverIP, setServerIP] = useState('192.168.1.66');
  const [connected, setConnected] = useState(false);
  const [hudStatus, setHudStatus] = useState('online'); // 'online' or 'offline'
  const [clock, setClock] = useState('');
  const [pairingCode, setPairingCode] = useState('');
  const [showPairModal, setShowPairModal] = useState(false);
  const [pendingIP, setPendingIP] = useState('');

  // ─── Load Settings on Mount ────────────────────────────
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const savedIP = await AsyncStorage.getItem('serverIP');
        const savedConnected = await AsyncStorage.getItem('connected');
        const savedPairCode = await AsyncStorage.getItem('pairingCode');
        
        if (savedIP) setServerIP(savedIP);
        if (savedPairCode) setPairingCode(savedPairCode);
        if (savedConnected === 'true' && savedIP) {
          testConnection(savedIP, savedPairCode || '');
        }

        // Check for native actions (like pick_file from overlay)
        if (HudBridge) {
          const action = await HudBridge.getAction();
          if (action === 'pick_file') {
            console.log('[HUD] Action detected: pick_file');
            pickAndUploadFile();
          }
        }
      } catch (e) {
        console.log('Error loading settings', e);
      }
    };
    loadSettings();
  }, []);



  // Files
  const [files, setFiles] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  // Clipboard
  const [clipboardText, setClipboardText] = useState('');
  const [clipStatus, setClipStatus] = useState('');

  // Animation
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const [slideshowCount, setSlideshowCount] = useState(0);

  const getBaseUrl = useCallback((targetIP = serverIP) => {
    return `http://${targetIP}:${SERVER_PORT}`;
  }, [serverIP]);

  const configureSlideshow = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'image/*',
        multiple: true,
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;

      const uris = result.assets.map(a => {
        let uri = a.uri;
        if (Platform.OS === 'android' && !uri.startsWith('content://') && !uri.startsWith('file://')) {
          uri = `file://${uri}`;
        }
        return uri;
      });
      
      setSlideshowCount(uris.length);
      setSlideshowImages(uris);
      Alert.alert('Slideshow Updated', `Added ${uris.length} images to bubble slideshow.`);
    } catch (e) {
      console.log('Slideshow config error:', e);
      Alert.alert('Error', 'Failed to configure slideshow');
    }
  };

  // ─── Clock ─────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');
      const s = String(now.getSeconds()).padStart(2, '0');
      setClock(`${h}:${m}:${s}`);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // ─── Pulse Animation ──────────────────────────────────
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.05, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();
  }, [pulseAnim]);

  // ─── Bubble Setup ──────────────────────────────────────
  useEffect(() => {
    try {
      checkPermission()
        .then(value => setHasPermission(value))
        .catch(console.error);
    } catch (err) {
      console.log('Native module RNFloatingBubble not loaded:', err.message);
    }

    const pressListener = DeviceEventEmitter.addListener('floating-bubble-press', () => {
      console.log('HUD Bubble Pressed! Launching Overlay...');
      if (HudBridge) HudBridge.showPanel();
    });
    const removeListener = DeviceEventEmitter.addListener('floating-bubble-remove', () => {
      setIsBubbleVisible(false);
    });
    return () => {
      pressListener.remove();
      removeListener.remove();
    };
  }, []);

  // ─── Fetch Stats from Desktop Server ───────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      // Laptop files only if connected
      if (connected) {
        loadFiles().catch(() => {});
      }
    }, 8000);
    
    if (connected) {
      loadFiles().catch(() => {});
    }
    return () => clearInterval(interval);
  }, [connected]);


  // ─── API Functions ─────────────────────────────────────
  const testConnection = async (targetIP, targetCode = pairingCode) => {
    if (typeof targetIP !== 'string') targetIP = serverIP;
    
    if (!targetIP) {
      Alert.alert('Missing Info', 'Enter your laptop IP address');
      return;
    }
    const baseUrl = `http://${targetIP}:${SERVER_PORT}`;
    console.log(`[HUD] Attempting connection to ${baseUrl}/api/status`);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log('[HUD] Connection attempt timed out');
        controller.abort();
      }, 10000); // 10s timeout
      
      const res = await fetch(`${baseUrl}/api/status`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      console.log(`[HUD] Response received: ${res.status}`);
      
      if (res.ok) {
        const data = await res.json();
        console.log(`[HUD] Status data:`, data);
        setHudStatus(data.status); 
        
        // Now check auth
        const authRes = await fetch(`${baseUrl}/api/auth/${targetCode}`);
        if (authRes.ok) {
          setServerIP(targetIP);
          setPairingCode(targetCode);
          AsyncStorage.setItem('serverIP', targetIP);
          AsyncStorage.setItem('pairingCode', targetCode);
          if (HudBridge) HudBridge.saveServerIP(targetIP).catch(() => {});
          
          if (data.status === 'online') {
            setConnected(true);
            AsyncStorage.setItem('connected', 'true');
            if (HudBridge) HudBridge.setConnected(true).catch(() => {});
            Alert.alert('Authenticated! ⚔', `Secure connection established with ${targetIP}`);
            loadFiles(targetIP, targetCode);
          } else {
            setConnected(true);
            Alert.alert('HUD Offline', 'Laptop HUD is in offline mode.');
          }
        } else {
          setPendingIP(targetIP);
          setShowPairModal(true);
        }
      } else {
        Alert.alert('Server Error', `HTTP ${res.status} returned by laptop`);
      }
    } catch (e) {
      console.log('[HUD] Connection error:', e.message);
      setConnected(false);
      AsyncStorage.setItem('connected', 'false');
      if (HudBridge) HudBridge.setConnected(false).catch(() => {});
      Alert.alert('Connection Failed', `Cannot reach laptop.\nMake sure laptop HUD is running & connected via WiFi.\n(${e.message})`);
    }
  };

  const disconnect = () => {
    setConnected(false);
    setPairingCode('');
    AsyncStorage.removeItem('connected');
    AsyncStorage.removeItem('pairingCode');
    if (HudBridge) HudBridge.setConnected(false).catch(() => {});
    Alert.alert('Disconnected', 'Secure session cleared.');
  };

  const getAuthHeader = (code = pairingCode) => ({
    'Authorization': `Bearer ${code}`
  });

  const loadFiles = async (targetIP = serverIP, code = pairingCode) => {
    if (!targetIP) return;
    try {
      const res = await fetch(`${getBaseUrl(targetIP)}/api/files`, {
        headers: getAuthHeader(code)
      });
      if (res.status === 401) {
        setConnected(false);
        setShowPairModal(true);
        return;
      }
      if (res.ok) {
        setHudStatus('online');
        const data = await res.json();
        setFiles(data);
      }
    } catch (e) {
      console.log('Files fetch error:', e);
    }
  };

  const deleteFile = async (name) => {
    Alert.alert('Delete', `Delete ${name}?`, [
      { text: 'Cancel' },
      {
        text: 'Delete', style: 'destructive', onPress: async () => {
          try {
            const res = await fetch(`${getBaseUrl()}/api/delete/${encodeURIComponent(name)}`, {
              method: 'DELETE',
              headers: getAuthHeader()
            });
            if (res.status === 401) throw new Error('Unauthorized');
            loadFiles();
          } catch (e) {
            Alert.alert('Error', 'Failed to delete file');
          }
        }
      },
    ]);
  };

  const downloadFile = (name) => {
    const url = `${getBaseUrl()}/download/${encodeURIComponent(name)}`;
    Linking.openURL(url);
  };

  const sendClipboard = async () => {
    try {
      const res = await fetch(`${getBaseUrl()}/api/clipboard`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify({ text: clipboardText }),
      });
      if (res.status === 401) throw new Error('Unauthorized');
      setClipStatus('✅ Sent to laptop!');
      setTimeout(() => setClipStatus(''), 3000);
    } catch (e) {
      setClipStatus('❌ Failed to send');
    }
  };

  const pickAndUploadFile = async () => {
    if (!connected) {
      Alert.alert('Not Connected', 'Please connect to your laptop first from settings.');
      return;
    }
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;

      let fileLocal = result.assets[0];
      const formData = new FormData();
      
      let uri = fileLocal.uri;
      if (Platform.OS === 'android' && !uri.startsWith('content://') && !uri.startsWith('file://')) {
        uri = `file://${uri}`;
      }

      setRefreshing(true);
      console.log(`[HUD] Uploading ${fileLocal.name} | URI: ${uri}`);

      const uploadUrl = `${getBaseUrl()}/upload`;
      const uploadResult = await FileSystem.uploadAsync(uploadUrl, uri, {
        fieldName: 'file',
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        mimeType: fileLocal.mimeType || 'application/octet-stream',
        headers: getAuthHeader()
      });

      setRefreshing(false);
      if (uploadResult.status === 200) {
        Alert.alert('Success! ⚔', `${fileLocal.name} sent to laptop.`);
        loadFiles();
      } else {
        console.log(`[HUD] Upload failed: ${uploadResult.status} - ${uploadResult.body}`);
        Alert.alert('Upload Failed', `Server error: ${uploadResult.status}`);
      }

    } catch (e) {
      console.log('[HUD] Upload error:', e);
      Alert.alert('Upload Error', e.message);
    } finally {
      // refreshing is set in callbacks for XHR
    }
  };

  const loadClipboard = async () => {
    try {
      const res = await fetch(`${getBaseUrl()}/api/clipboard`, {
        headers: getAuthHeader()
      });
      if (res.status === 401) {
        setConnected(false);
        setShowPairModal(true);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setClipboardText(data.text || '');
        setClipStatus('📋 Refreshed from laptop!');
        setTimeout(() => setClipStatus(''), 3000);
      }
    } catch (e) {
      setClipStatus('❌ Failed to load');
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadFiles();
    setRefreshing(false);
  };

  // ─── Bubble Controls ──────────────────────────────────
  const handleRequestPermission = () => {
    try {
      requestPermission()
        .then(() => setHasPermission(true))
        .catch(() => Alert.alert('Permission Denied'));
    } catch (err) {
      Alert.alert('Native Module Missing', 'You are likely running in Expo Go. The custom bubble module requires to be built as a native app.');
    }
  };

  const toggleBubble = () => {
    try {
      if (!isBubbleVisible) {
        initialize()
          .then(() => showFloatingBubble(10, 10))
          .then(() => setIsBubbleVisible(true))
          .catch(console.error);
      } else {
        hideFloatingBubble()
          .then(() => setIsBubbleVisible(false))
          .catch(console.error);
      }
    } catch (err) {
      Alert.alert('Native Module Missing', 'You are likely running in Expo Go. The custom bubble module requires to be built as a native app.');
    }
  };

  // ═══════════════════════════════════════════════════════
  //  RENDER
  // ═══════════════════════════════════════════════════════
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={BG} />

      {/* ─── Intro Overlay ─── */}
      {showIntro && (
        <Animated.View style={[styles.introContainer, { opacity: introFade }]}>
          <Animated.View style={{ transform: [{ scale: introScale }], alignItems: 'center' }}>
            <Image 
              source={require('./assets/logo.png')} 
              style={styles.introImage}
              resizeMode="contain"
            />
            <Text style={styles.introLogo}>⚔ HUD</Text>
            <View style={styles.introUnderline} />
            <Text style={styles.introSubText}>MAXIMUM EFFORT</Text>
          </Animated.View>
        </Animated.View>
      )}

      {/* ─── Pairing Modal ─── */}
      {showPairModal && (
        <View style={styles.modalOverlay}>
          <View style={styles.authModal}>
            <Text style={styles.modalTitle}>⚔ SECURITY PAIRING</Text>
            <Text style={styles.modalDesc}>Enter the 6-digit code shown on your Laptop HUD</Text>
            <TextInput
              style={styles.authInput}
              placeholder="000000"
              placeholderTextColor="#444"
              keyboardType="number-pad"
              maxLength={6}
              onChangeText={val => {
                if (val.length === 6) {
                  setShowPairModal(false);
                  testConnection(pendingIP, val);
                }
              }}
            />
            <TouchableOpacity onPress={() => setShowPairModal(false)}>
              <Text style={styles.cancelText}>CANCEL</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* ─── Header ─── */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>⚔ HUD</Text>
            <Text style={styles.subtitle}>Maximum Effort dashboard</Text>
          </View>
          <View style={styles.clockBox}>
            <Text style={styles.clockText}>{clock}</Text>
            <View style={[
              styles.statusDot, 
              { backgroundColor: !connected ? RED : (hudStatus === 'online' ? GREEN : '#FFA500') }
            ]} />
          </View>
        </View>
        <View style={styles.headerLine} />
      </View>

      {/* ─── Tab Bar ─── */}
      <View style={styles.tabBar}>
        {['dashboard', 'files', 'clipboard', 'settings'].map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
              {tab === 'dashboard' ? '📊' : tab === 'files' ? '📁' : tab === 'clipboard' ? '📋' : '⚙'}
            </Text>
            <Text style={[styles.tabLabel, activeTab === tab && styles.tabLabelActive]}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══════════════════════════════════════════════ */}
        {/*  DASHBOARD TAB                                  */}
        {/* ═══════════════════════════════════════════════ */}
        {activeTab === 'dashboard' && (
          <View>
            {/* Bubble Control */}
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>OVERLAY CONTROL</Text>
              <View style={styles.statusRow}>
                <Animated.View style={[styles.bubblePreview, { transform: [{ scale: pulseAnim }] }]}>
                  <Text style={{ fontSize: 24, color: ACCENT, fontWeight: 'bold' }}>D</Text>
                </Animated.View>
                <View style={styles.statusInfo}>
                  <Text style={[styles.statusValue, isBubbleVisible ? { color: ACCENT } : { color: '#444' }]}>
                    {isBubbleVisible ? 'ACTIVE' : 'INACTIVE'}
                  </Text>
                  <Text style={styles.statusHint}>Floating Bubble Overlay</Text>
                </View>
              </View>
              {!hasPermission ? (
                <TouchableOpacity style={styles.btn} onPress={handleRequestPermission}>
                  <Text style={styles.btnText}>🔓 GRANT OVERLAY PERMISSION</Text>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  style={[styles.btn, isBubbleVisible && styles.btnOutline]}
                  onPress={toggleBubble}
                >
                  <Text style={[styles.btnText, isBubbleVisible && styles.btnTextOutline]}>
                    {isBubbleVisible ? '✕ REMOVE BUBBLE' : '⚔ LAUNCH BUBBLE'}
                  </Text>
                </TouchableOpacity>
              )}

              {/* Slideshow config */}
              {hasPermission && (
                <TouchableOpacity
                  style={[styles.btn, { marginTop: 10, backgroundColor: '#444' }]}
                  onPress={configureSlideshow}
                >
                  <Text style={styles.btnText}>
                    🖼 CONFIGURE SLIDESHOW ({slideshowCount})
                  </Text>
                </TouchableOpacity>
              )}
            </View>



            {/* Connection Status */}
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>⚔ DESKTOP LINK</Text>
              <View style={styles.connectionRow}>
                <View style={[styles.connectionDot, { backgroundColor: connected ? GREEN : '#333' }]} />
                <Text style={styles.connectionText}>
                  {connected ? `Connected to ${serverIP}` : 'Not connected to desktop'}
                </Text>
              </View>
              {connected && (
                <View>
                  <Text style={styles.connectionHint}>
                    📂 Files & Clipboard synced with laptop
                  </Text>
                  <TouchableOpacity 
                    style={[styles.btn, styles.btnSmall, { marginTop: 10, backgroundColor: ACCENT }]}
                    onPress={pickAndUploadFile}
                  >
                    <Text style={styles.btnText}>📤 SEND FILE TO LAPTOP</Text>
                  </TouchableOpacity>
                </View>
              )}
              {!connected && (
                <TouchableOpacity
                  style={[styles.btn, styles.btnSmall]}
                  onPress={() => setActiveTab('settings')}
                >
                  <Text style={styles.btnText}>CONNECT TO DESKTOP →</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}

        {/* ═══════════════════════════════════════════════ */}
        {/*  FILES TAB                                      */}
        {/* ═══════════════════════════════════════════════ */}
        {activeTab === 'files' && (
          <View>
            {!connected ? (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyIcon}>🔗</Text>
                <Text style={styles.emptyText}>Connect to your desktop first</Text>
                <TouchableOpacity style={[styles.btn, styles.btnSmall]} onPress={() => setActiveTab('settings')}>
                  <Text style={styles.btnText}>GO TO SETTINGS</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View>
                <View style={styles.card}>
                  <Text style={styles.sectionTitle}>📂 SHARED FILES</Text>
                  {hudStatus === 'offline' && (
                    <View style={styles.offlineBox}>
                      <Text style={styles.offlineText}>⚠️ HUD IS OFFLINE (MINI-MODE)</Text>
                      <Text style={styles.offlineHint}>Click the indicator icon on your laptop to turn it on.</Text>
                    </View>
                  )}
                  <Text style={styles.fileCount}>{files.length} file{files.length !== 1 ? 's' : ''} on desktop</Text>
                  <View style={styles.filesTabActions}>
                    <TouchableOpacity style={[styles.btn, styles.btnSmall, { flex: 1, marginRight: 8 }]} onPress={onRefresh}>
                      <Text style={styles.btnText}>🔄 REFRESH</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={[styles.btn, styles.btnSmall, { flex: 1, backgroundColor: ACCENT }]} onPress={pickAndUploadFile}>
                      {refreshing ? (
                        <ActivityIndicator size="small" color="#fff" />
                      ) : (
                        <Text style={styles.btnText}>📤 SEND FILES</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>

                {files.length === 0 ? (
                  <View style={styles.emptyCard}>
                    <Text style={styles.emptyIcon}>📭</Text>
                    <Text style={styles.emptyText}>No files shared yet</Text>
                    <Text style={styles.emptyHint}>Drop files in ~/Desktop/Sys-Mob on your laptop</Text>
                  </View>
                ) : (
                  files.map((file, i) => (
                    <View key={i} style={styles.fileItem}>
                      <Text style={styles.fileIcon}>{getFileIcon(file.name)}</Text>
                      <View style={styles.fileInfo}>
                        <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
                        <Text style={styles.fileSize}>{file.size}</Text>
                      </View>
                      <View style={styles.fileActions}>
                        <TouchableOpacity style={styles.fileBtn} onPress={() => downloadFile(file.name)}>
                          <Text style={styles.fileBtnText}>↓</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={[styles.fileBtn, styles.fileBtnDel]} onPress={() => deleteFile(file.name)}>
                          <Text style={styles.fileBtnText}>✕</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))
                )}
              </View>
            )}
          </View>
        )}

        {/* ═══════════════════════════════════════════════ */}
        {/*  CLIPBOARD TAB                                  */}
        {/* ═══════════════════════════════════════════════ */}
        {activeTab === 'clipboard' && (
          <View>
            {!connected ? (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyIcon}>🔗</Text>
                <Text style={styles.emptyText}>Connect to your desktop first</Text>
                <TouchableOpacity style={[styles.btn, styles.btnSmall]} onPress={() => setActiveTab('settings')}>
                  <Text style={styles.btnText}>GO TO SETTINGS</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>📋 SHARED CLIPBOARD</Text>
                {hudStatus === 'offline' && (
                  <View style={styles.offlineBox}>
                    <Text style={styles.offlineText}>⚠️ HUD IS OFFLINE (MINI-MODE)</Text>
                    <Text style={styles.offlineHint}>Click the icon on your laptop to sync clipboard.</Text>
                  </View>
                )}
                <TextInput
                  style={styles.clipInput}
                  value={clipboardText}
                  onChangeText={setClipboardText}
                  placeholder="Type or paste text here to share..."
                  placeholderTextColor="#444"
                  multiline
                  numberOfLines={6}
                  textAlignVertical="top"
                />
                <View style={styles.clipActions}>
                  <TouchableOpacity style={[styles.btn, { flex: 1.5, marginRight: 8 }]} onPress={sendClipboard}>
                    <Text style={styles.btnText}>📤 SEND TO LAPTOP</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[styles.btn, styles.btnOutline, { flex: 1 }]} onPress={loadClipboard}>
                    <Text style={[styles.btnText, styles.btnTextOutline]}>� REFRESH</Text>
                  </TouchableOpacity>
                </View>
                {clipStatus ? (
                  <Text style={styles.clipStatus}>{clipStatus}</Text>
                ) : null}
              </View>
            )}
          </View>
        )}

        {/* ═══════════════════════════════════════════════ */}
        {/*  SETTINGS TAB                                   */}
        {/* ═══════════════════════════════════════════════ */}
        {activeTab === 'settings' && (
          <View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>🔗 DESKTOP CONNECTION</Text>
              <Text style={styles.settingsHint}>
                Enter your laptop's IP address to connect.
              </Text>

              <Text style={styles.inputLabel}>LAPTOP IP ADDRESS</Text>
              <TextInput
                style={styles.settingsInput}
                value={serverIP}
                onChangeText={setServerIP}
                placeholder="e.g. 192.168.1.66"
                placeholderTextColor="#444"
                keyboardType="numeric"
              />

              <TouchableOpacity style={styles.btn} onPress={testConnection}>
                <Text style={styles.btnText}>
                  {connected ? '✅ RECONNECT' : '⚔ CONNECT TO DESKTOP'}
                </Text>
              </TouchableOpacity>

              {connected && (
                <TouchableOpacity 
                   style={[styles.btn, styles.btnOutline, { marginTop: 10, borderColor: RED }]} 
                   onPress={disconnect}
                >
                  <Text style={[styles.btnText, { color: RED }]}>🛑 DISCONNECT HUD</Text>
                </TouchableOpacity>
              )}

              {connected && (
                <View style={styles.connectedBox}>
                  <Text style={styles.connectedText}>✅ Connected to {serverIP}:{SERVER_PORT}</Text>
                </View>
              )}
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>📱 APP INFO</Text>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>App</Text>
                <Text style={styles.infoValue}>HUD Mobile</Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Version</Text>
                <Text style={styles.infoValue}>1.0.0</Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Server Port</Text>
                <Text style={styles.infoValue}>{SERVER_PORT}</Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Bubble</Text>
                <Text style={[styles.infoValue, { color: isBubbleVisible ? GREEN : RED }]}>
                  {isBubbleVisible ? 'Active' : 'Inactive'}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Bottom padding */}
        <View style={{ height: 40 }} />
      </ScrollView>

      {/* ─── Footer ─── */}
      <View style={styles.footer}>
        <View style={styles.footerLine} />
        <Text style={styles.footerText}>Maximum Effort Dashboard • Mobile</Text>
      </View>
    </View>
  );
}

// ═══════════════════════════════════════════════════════════
//  STYLES
// ═══════════════════════════════════════════════════════════
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: BG,
  },

  // Header
  header: {
    paddingTop: Platform.OS === 'android' ? 44 : 60,
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '900',
    color: ACCENT,
    letterSpacing: 2,
    textShadowColor: 'rgba(230, 33, 23, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 15,
  },
  subtitle: {
    fontSize: 10,
    color: DIM,
    marginTop: 2,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  clockBox: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  clockText: {
    color: DIM,
    fontSize: 14,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier',
    fontWeight: 'bold',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginLeft: 8,
  },
  headerLine: {
    height: 1,
    backgroundColor: ACCENT,
    marginTop: 12,
    shadowColor: ACCENT,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 3,
  },

  // Tab Bar
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginVertical: 8,
    backgroundColor: BG2,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1a1a1a',
    overflow: 'hidden',
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: ACCENT,
  },
  tabText: {
    fontSize: 16,
  },
  tabTextActive: {},
  tabLabel: {
    fontSize: 8,
    color: DIM,
    marginTop: 2,
    fontWeight: 'bold',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  tabLabelActive: {
    color: 'white',
  },

  // Scroll
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
  },

  // Cards
  card: {
    backgroundColor: BG2,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#1a1a1a',
    padding: 16,
    marginBottom: 12,
  },
  sectionTitle: {
    color: ACCENT,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 12,
    textTransform: 'uppercase',
  },

  // Status / Bubble
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  bubblePreview: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#1a0000',
    borderWidth: 2,
    borderColor: ACCENT,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
    shadowColor: ACCENT,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 5,
  },
  statusInfo: {},
  statusValue: {
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 3,
  },
  statusHint: {
    color: DIM,
    fontSize: 10,
    marginTop: 2,
  },

  // Gauges
  gaugeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  ramInfo: {
    color: DIM,
    fontSize: 9,
    textAlign: 'center',
    marginTop: 4,
  },

  // Network
  netRow: {
    flexDirection: 'row',
  },
  netBox: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
  },
  netLabel: {
    color: DIM,
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  netValue: {
    fontSize: 16,
    fontWeight: '900',
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier',
  },

  // Connection
  connectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  connectionDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 10,
  },
  connectionText: {
    color: TEXT,
    fontSize: 13,
    fontWeight: '600',
  },
  connectionHint: {
    color: DIM,
    fontSize: 11,
    marginBottom: 8,
  },

  // Buttons
  btn: {
    backgroundColor: ACCENT,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: ACCENT,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  btnSmall: {
    paddingVertical: 10,
  },
  btnOutline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: ACCENT,
    shadowOpacity: 0,
    elevation: 0,
  },
  btnText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
    letterSpacing: 1.5,
  },
  btnTextOutline: {
    color: ACCENT,
  },

  // Empty
  emptyCard: {
    backgroundColor: BG2,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#1a1a1a',
    padding: 40,
    alignItems: 'center',
    marginBottom: 12,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  emptyText: {
    color: '#555',
    fontSize: 14,
    marginBottom: 6,
  },
  emptyHint: {
    color: '#333',
    fontSize: 11,
    textAlign: 'center',
    marginBottom: 16,
  },

  // Files
  fileItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: BG2,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1a1a1a',
    padding: 12,
    marginBottom: 8,
  },
  fileIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    color: TEXT,
    fontSize: 13,
    fontWeight: '600',
  },
  fileSize: {
    color: DIM,
    fontSize: 10,
    marginTop: 2,
  },
  fileActions: {
    flexDirection: 'row',
    gap: 6,
  },
  fileBtn: {
    backgroundColor: ACCENT,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  fileBtnDel: {
    backgroundColor: '#333',
  },
  fileBtnText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  fileCount: {
    color: DIM,
    fontSize: 11,
    marginBottom: 8,
  },

  // Clipboard
  clipInput: {
    backgroundColor: '#0a0a0a',
    borderWidth: 1,
    borderColor: '#1a1a1a',
    borderRadius: 10,
    color: TEXT,
    padding: 14,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier',
    fontSize: 13,
    minHeight: 120,
    marginBottom: 8,
  },
  clipActions: {
    gap: 8,
  },
  clipStatus: {
    color: GREEN,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 10,
    fontWeight: '600',
  },
  filesTabActions: {
    flexDirection: 'row',
    marginTop: 10,
  },


  // Settings
  settingsHint: {
    color: DIM,
    fontSize: 11,
    marginBottom: 16,
    lineHeight: 16,
  },
  inputLabel: {
    color: DIM,
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginBottom: 6,
    marginTop: 4,
  },
  settingsInput: {
    backgroundColor: '#0a0a0a',
    borderWidth: 1,
    borderColor: '#1a1a1a',
    borderRadius: 10,
    color: TEXT,
    padding: 14,
    fontSize: 16,
    marginBottom: 12,
    fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier',
  },
  connectedBox: {
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(76, 175, 80, 0.3)',
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
    alignItems: 'center',
  },
  connectedText: {
    color: GREEN,
    fontSize: 13,
    fontWeight: '600',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  infoLabel: {
    color: DIM,
    fontSize: 12,
  },
  infoValue: {
    color: TEXT,
    fontSize: 12,
    fontWeight: '600',
  },

  // Footer
  footer: {
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  footerLine: {
    height: 1,
    backgroundColor: ACCENT,
    marginBottom: 8,
  },
  footerText: {
    color: '#333',
    fontSize: 9,
    textAlign: 'center',
    letterSpacing: 1,
  },
  offlineBox: {
    backgroundColor: 'rgba(255, 165, 0, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(255, 165, 0, 0.3)',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  offlineText: {
    color: '#FFA500',
    fontSize: 11,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 4,
  },
  offlineHint: {
    color: DIM,
    fontSize: 10,
    textAlign: 'center',
  },
  // Intro Styles
  introContainer: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#000',
    zIndex: 99999,
    justifyContent: 'center',
    alignItems: 'center',
  },
  introLogo: {
    color: '#ED1C24',
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: 4,
    textShadowColor: 'rgba(237, 28, 36, 0.8)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 15,
  },
  introUnderline: {
    height: 3,
    width: 60,
    backgroundColor: '#ED1C24',
    marginTop: 8,
    borderRadius: 2,
  },
  introSubText: {
    color: '#666',
    fontSize: 12,
    letterSpacing: 6,
    marginTop: 15,
    fontWeight: 'bold',
  },
  introImage: {
    height: 150,
    marginBottom: 20,
  },
  modalOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.85)',
    zIndex: 10000,
    justifyContent: 'center',
    alignItems: 'center',
  },
  authModal: {
    width: '80%',
    backgroundColor: BG2,
    borderRadius: 20,
    padding: 25,
    borderWidth: 2,
    borderColor: ACCENT,
    alignItems: 'center',
  },
  modalTitle: {
    color: ACCENT,
    fontSize: 18,
    fontWeight: '900',
    marginBottom: 10,
  },
  modalDesc: {
    color: DIM,
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 20,
  },
  authInput: {
    backgroundColor: '#000',
    width: '100%',
    height: 60,
    borderRadius: 12,
    color: TEXT,
    fontSize: 32,
    textAlign: 'center',
    fontWeight: 'bold',
    letterSpacing: 8,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#222',
  },
  cancelText: {
    color: DIM,
    fontSize: 11,
    fontWeight: 'bold',
  },
  disconnectBtn: {
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#300',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  disconnectText: {
    color: '#e62117',
    fontSize: 11,
    fontWeight: 'bold',
  },
});

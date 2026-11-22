import React from "react";
import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";

const tiles = [
  { icon: "✦", title: "Nexo AI", detail: "Tu asistente personal", color: "#8C7CFF" },
  { icon: "◷", title: "Mi día", detail: "Planes y recordatorios", color: "#67C7F5" },
  { icon: "◎", title: "Mis metas", detail: "Ideas y proyectos", color: "#5ED6A5" },
  { icon: "⌁", title: "Finanzas", detail: "Tu panorama financiero", color: "#F3C66A" },
];

export default function App() {
  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <Text style={styles.eyebrow}>EDWARD TEJADA · PRODUCTO EN DESARROLLO</Text>
          <Text style={styles.brand}>NEXO<Text style={styles.dot}>.</Text></Text>
          <Text style={styles.subtitle}>Un lugar para conectar todo lo que importa.</Text>
        </View>

        <View style={styles.hero}>
          <Text style={styles.heroLabel}>TU ESPACIO PERSONAL</Text>
          <Text style={styles.heroTitle}>¿Qué quieres lograr hoy?</Text>
          <Text style={styles.heroCopy}>Tu vida, tus ideas y tus planes. En un solo lugar.</Text>
          <View style={styles.prompt}>
            <Text style={styles.promptText}>Escribe una idea o tarea…</Text>
            <View style={styles.promptButton}><Text style={styles.promptButtonText}>↑</Text></View>
          </View>
          <Text style={styles.note}>La IA y las acciones inteligentes se habilitarán en futuras fases.</Text>
        </View>

        <Text style={styles.sectionTitle}>TU CENTRO DE CONTROL</Text>
        <View style={styles.grid}>
          {tiles.map((tile) => (
            <View key={tile.title} style={styles.tile}>
              <View style={[styles.tileIcon, { borderColor: tile.color }]}><Text style={{ color: tile.color, fontSize: 21 }}>{tile.icon}</Text></View>
              <Text style={styles.tileTitle}>{tile.title}</Text>
              <Text style={styles.tileDetail}>{tile.detail}</Text>
            </View>
          ))}
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerLine}>PRIVACIDAD · SEGURIDAD · CONTROL</Text>
          <Text style={styles.signature}>Creado por Edward Tejada</Text>
          <Text style={styles.footerHint}>Prototipo inicial — no guarda datos ni envía información.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#090B11" },
  container: { padding: 22, paddingTop: 36, paddingBottom: 42 },
  header: { marginBottom: 26 },
  eyebrow: { color: "#9298AC", fontSize: 10, letterSpacing: 2, fontWeight: "700" },
  brand: { color: "#F6F7FB", fontSize: 44, fontWeight: "800", letterSpacing: 3, marginTop: 10 },
  dot: { color: "#8C7CFF" },
  subtitle: { color: "#AEB4C6", fontSize: 14, marginTop: 4 },
  hero: { backgroundColor: "#141824", borderWidth: 1, borderColor: "#252D40", borderRadius: 22, padding: 20, marginBottom: 28 },
  heroLabel: { color: "#8C7CFF", fontSize: 10, fontWeight: "700", letterSpacing: 1.7 },
  heroTitle: { color: "#F5F6FA", fontSize: 23, fontWeight: "700", marginTop: 10 },
  heroCopy: { color: "#AEB4C6", fontSize: 13, lineHeight: 20, marginTop: 8 },
  prompt: { borderColor: "#343C50", borderWidth: 1, borderRadius: 14, padding: 12, marginTop: 18, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  promptText: { color: "#7F879C", fontSize: 13 },
  promptButton: { backgroundColor: "#8C7CFF", borderRadius: 9, width: 32, height: 32, alignItems: "center", justifyContent: "center" },
  promptButtonText: { color: "#090B11", fontSize: 19, fontWeight: "700" },
  note: { color: "#777F94", fontSize: 10, marginTop: 12 },
  sectionTitle: { color: "#B5BCD0", fontSize: 11, fontWeight: "700", letterSpacing: 1.5, marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tile: { backgroundColor: "#111620", borderWidth: 1, borderColor: "#252D3D", borderRadius: 17, padding: 15, width: "48%", minHeight: 145 },
  tileIcon: { borderWidth: 1, borderRadius: 12, width: 40, height: 40, alignItems: "center", justifyContent: "center", backgroundColor: "#181D2A" },
  tileTitle: { color: "#F3F5FA", fontWeight: "700", fontSize: 14, marginTop: 13 },
  tileDetail: { color: "#969EB3", fontSize: 11, marginTop: 5, lineHeight: 16 },
  footer: { marginTop: 32, alignItems: "center" },
  footerLine: { color: "#767F95", fontSize: 9, letterSpacing: 1.4 },
  signature: { color: "#D6D9E4", fontSize: 12, marginTop: 10, fontWeight: "600" },
  footerHint: { color: "#5F687D", fontSize: 10, marginTop: 7, textAlign: "center" }
});
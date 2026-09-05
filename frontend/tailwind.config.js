/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // High-end Stripe/Ramp neutral palette
        "surface": "#f8fafc",                  // crisp slate-50 background
        "surface-dim": "#f1f5f9",              // slate-100
        "surface-bright": "#ffffff",
        "surface-container-lowest": "#ffffff", // pure white cards
        "surface-container-low": "#f8fafc",    // subtle inner containers
        "surface-container": "#f1f5f9",        // slate-100 pills & hover
        "surface-container-high": "#e2e8f0",   // slate-200 badges
        "surface-container-highest": "#cbd5e1",// slate-300
        "on-surface": "#0f172a",               // slate-900 high contrast readable text
        "on-surface-variant": "#475569",       // slate-600 secondary text
        "inverse-surface": "#0f172a",
        "inverse-on-surface": "#f8fafc",
        "outline": "#94a3b8",                  // slate-400 borders
        "outline-variant": "#e2e8f0",          // crisp 1px borders (slate-200)
        "surface-tint": "#0284c7",
        
        // Primary obsidian black for enterprise CTAs
        "primary": "#0f172a",
        "on-primary": "#ffffff",
        "primary-container": "#1e293b",
        "on-primary-container": "#94a3b8",
        
        // Secondary fintech blue (Stripe / Razorpay precision blue)
        "secondary": "#0284c7",                // sky-600
        "on-secondary": "#ffffff",
        "secondary-container": "#e0f2fe",
        "on-secondary-container": "#0369a1",
        "secondary-fixed": "#e0f2fe",          // sky-100
        "secondary-fixed-dim": "#bae6fd",      // sky-200
        "on-secondary-fixed": "#0369a1",       // sky-700
        "on-secondary-fixed-variant": "#075985",
        
        // Semantic alert red
        "error": "#dc2626",                    // red-600
        "error-container": "#fee2e2",          // red-100
        "on-error": "#ffffff",
        "on-error-container": "#991b1b",       // red-800
        
        "background": "#f8fafc",
        "on-background": "#0f172a"
      },
      spacing: {
        "spacing-2xs": "2px",
        "spacing-xs": "4px",
        "spacing-sm": "8px",
        "spacing-md": "12px",
        "spacing-base": "16px",
        "spacing-lg": "20px",
        "spacing-xl": "24px",
        "spacing-2xl": "32px",
        "row-height-compact": "32px",
        "row-height-standard": "40px",
        "sidebar-width": "240px",
        "drawer-width-md": "480px",
        "drawer-width-lg": "640px"
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        "body-default": ["Inter", "sans-serif"],
        "headline-lg": ["Inter", "sans-serif"],
        "headline-md": ["Inter", "sans-serif"],
        "headline-sm": ["Inter", "sans-serif"],
        "body-medium": ["Inter", "sans-serif"],
        "body-sm": ["Inter", "sans-serif"],
        "body-xs": ["Inter", "sans-serif"],
        "label-mono-sm": ["JetBrains Mono", "monospace"],
        "label-mono-xs": ["JetBrains Mono", "monospace"],
        "metric-display": ["Inter", "sans-serif"]
      },
      fontSize: {
        "body-default": ["13px", { lineHeight: "18px", letterSpacing: "-0.005em", fontWeight: "400" }],
        "headline-lg": ["20px", { lineHeight: "26px", letterSpacing: "-0.02em", fontWeight: "600" }],
        "headline-md": ["16px", { lineHeight: "22px", letterSpacing: "-0.015em", fontWeight: "600" }],
        "headline-sm": ["14px", { lineHeight: "20px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "body-medium": ["13px", { lineHeight: "18px", letterSpacing: "-0.005em", fontWeight: "500" }],
        "body-sm": ["12px", { lineHeight: "16px", letterSpacing: "0em", fontWeight: "400" }],
        "body-xs": ["11px", { lineHeight: "15px", letterSpacing: "0.005em", fontWeight: "400" }],
        "label-mono-sm": ["12px", { lineHeight: "16px", letterSpacing: "-0.02em", fontWeight: "500" }],
        "label-mono-xs": ["11px", { lineHeight: "14px", letterSpacing: "-0.01em", fontWeight: "500" }],
        "metric-display": ["26px", { lineHeight: "32px", letterSpacing: "-0.03em", fontWeight: "700" }]
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(15, 23, 42, 0.04)',
        'sm': '0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04)',
        'md': '0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)',
        'lg': '0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)',
        'card': '0 0 0 1px rgba(15, 23, 42, 0.06), 0 1px 2px 0 rgba(15, 23, 42, 0.04)',
        'card-hover': '0 0 0 1px rgba(15, 23, 42, 0.1), 0 4px 6px -1px rgba(15, 23, 42, 0.06)'
      }
    }
  },
  plugins: []
};

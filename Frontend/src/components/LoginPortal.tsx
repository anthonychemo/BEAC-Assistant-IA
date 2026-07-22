import React, { useState } from "react";
import { X, Lock, Mail, AlertTriangle, CheckCircle } from "lucide-react";
import { motion } from "motion/react";
import beacLogo from "../../assets/logo_BEAC.png";

interface LoginPortalProps {
  onClose: () => void;
  onLoginSuccess: () => void;
}

export default function LoginPortal({ onClose, onLoginSuccess }: LoginPortalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Institutional mock credentials
    if (email === "admin@beac.int" && password === "Cemac2026!") {
      setSuccess(true);
      setTimeout(() => {
        onLoginSuccess();
        onClose();
      }, 1000);
    } else {
      setError("Identifiants incorrects. Veuillez utiliser les informations d'authentification inscrites ci-dessous.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0D2D5E]/60 backdrop-blur-sm select-none">
      
      {/* Login Box */}
      <div className="relative w-full max-w-md bg-white border border-[#C8971A]/20 rounded-2xl shadow-2xl p-8 overflow-hidden">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full text-black/50 hover:text-black hover:bg-gray-100 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mt-2 mb-8">
          <div className="w-30 h-30 flex items-center justify-center mb-4">
            <img src={beacLogo} alt="Logo BEAC" className="w-full h-full object-contain" />
          </div>
          <h2 className="font-sans text-[#0D2D5E] text-xl font-extrabold tracking-tight">
            ESPACE ADMINISTRATEUR BEAC
          </h2>
          <p className="text-black/50 font-sans text-xs mt-1">
            Système d'administration sécurisé BEAC
          </p>
        </div>

        {success ? (
          <div className="py-8 flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-4 animate-scale-up">
              <CheckCircle className="w-6 h-6" />
            </div>
            <h3 className="font-sans text-emerald-800 text-base font-bold mb-1">Authentification validée</h3>
            <p className="text-xs text-gray-500">Ouverture de la console sécurisée...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error alerts */}
            {error && (
              <div className="p-3.5 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs leading-relaxed flex gap-2.5 items-start">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Email input field */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-gray-700 block font-sans">
                Identifiant professionnel
              </label>
              <div className="relative flex items-center bg-gray-50 border border-gray-200 rounded-lg p-3 py-2.5 focus-within:border-[#C8971A]/70 focus-within:bg-white transition-all">
                <Mail className="text-black/30 w-4 h-4 mr-2.5 shrink-0" />
                <input
                  type="email"
                  placeholder="nom@beac.int"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="bg-transparent border-none text-black placeholder:text-black/30 focus:outline-none w-full text-xs font-sans"
                />
              </div>
            </div>

            {/* Password input field */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-gray-700 block font-sans">
                Mot de passe sécurisé
              </label>
              <div className="relative flex items-center bg-gray-50 border border-gray-200 rounded-lg p-3 py-2.5 focus-within:border-[#C8971A]/70 focus-within:bg-white transition-all">
                <Lock className="text-black/30 w-4 h-4 mr-2.5 shrink-0" />
                <input
                  type="password"
                  placeholder="••••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="bg-transparent border-none text-black placeholder:text-black/30 focus:outline-none w-full text-xs font-sans"
                />
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              className="w-full bg-[#0D2D5E] hover:bg-[#00183e] text-[#C8971A] hover:text-white py-3 rounded-lg font-sans font-bold text-xs uppercase tracking-wider transition-all shadow-md mt-6 cursor-pointer"
            >
              Se Connecter
            </button>

            {/* Guided credentials hint */}
            <div className="mt-6 pt-5 border-t border-gray-100 bg-gray-50/50 p-4 rounded-lg select-text">
              <div className="text-[10px] font-bold text-[#0D2D5E] uppercase tracking-wide mb-1 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#C8971A]" />
                Identifiants de démonstration
              </div>
              <div className="text-[10px] text-gray-600 space-y-1 leading-relaxed">
                <div>• Identifiant : <strong className="font-mono text-[11px] text-black">admin@beac.int</strong></div>
                <div>• Mot de passe : <strong className="font-mono text-[11px] text-black">Cemac2026!</strong></div>
              </div>
            </div>
          </form>
        )}

      </div>
    </div>
  );
}

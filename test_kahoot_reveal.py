#!/usr/bin/env python3
"""
Script de test pour vérifier l'API de révélation des réponses Kahoot
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
SESSION_CODE = "12345678"  # Remplacez par un vrai code de session

def test_reveal_answers():
    """Test de l'API de révélation des réponses"""
    
    print("🧪 Test de l'API de révélation des réponses")
    print("=" * 50)
    
    # 1. Vérifier l'état initial
    print("1. Vérification de l'état initial...")
    try:
        response = requests.get(f"{BASE_URL}/kahoot/api/state/{SESSION_CODE}/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ État récupéré: phase={data.get('current_phase')}, answers_revealed={data.get('answers_revealed')}")
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
        return
    
    # 2. Révéler les réponses
    print("2. Révélation des réponses...")
    try:
        response = requests.post(
            f"{BASE_URL}/kahoot/api/host/reveal/{SESSION_CODE}/",
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Réponses révélées: {data}")
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
        return
    
    # 3. Vérifier l'état après révélation
    print("3. Vérification de l'état après révélation...")
    time.sleep(1)  # Attendre un peu
    try:
        response = requests.get(f"{BASE_URL}/kahoot/api/state/{SESSION_CODE}/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ État après révélation: phase={data.get('current_phase')}, answers_revealed={data.get('answers_revealed')}")
            
            if data.get('answers_revealed'):
                print("   ✅ Les réponses sont bien révélées!")
                if 'answer_stats' in data:
                    print(f"   📊 Statistiques disponibles: {data['answer_stats']}")
                else:
                    print("   ⚠️  Pas de statistiques disponibles")
            else:
                print("   ❌ Les réponses ne sont pas révélées")
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")

if __name__ == "__main__":
    test_reveal_answers()


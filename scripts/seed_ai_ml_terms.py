"""
Seed AI/ML Terms Script - Populate knowledge_base with 20 advanced AI/ML terms.

Tags: Class: Tech, Difficulty: Advanced
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from database.db_manager import KnowledgeBase, SessionLocal, init_db

# 20 Advanced AI/ML Terms with Japanese technical loanwords
AI_ML_TERMS = [
    {
        "concept_title": "Transformer Architecture",
        "japanese_term": "トランスフォーマーアーキテクチャ",
        "concept_content": """Transformer Architecture (トランスフォーマーアーキテクチャ)

A deep learning model architecture introduced in "Attention Is All You Need" (2017). 
Uses self-attention mechanisms to process sequences in parallel rather than sequentially.

Key Components:
- Self-Attention (セルフアテンション): Allows the model to weigh the importance of different parts of the input
- Multi-Head Attention (マルチヘッドアテンション): Multiple attention mechanisms run in parallel
- Positional Encoding (位置エンコーディング): Adds information about word order
- Feed-Forward Networks (フィードフォワードネットワーク): Processes attended features

Applications: GPT, BERT, modern language models

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Gradient Descent",
        "japanese_term": "勾配降下法",
        "concept_content": """Gradient Descent (勾配降下法 - こうばいこうかほう)

An optimization algorithm used to minimize a loss function by iteratively moving in the direction of steepest descent.

Types:
- Batch Gradient Descent (バッチ勾配降下法): Uses entire dataset
- Stochastic Gradient Descent (確率的勾配降下法): Uses one sample at a time
- Mini-Batch Gradient Descent (ミニバッチ勾配降下法): Uses small batches

Learning Rate (学習率): Controls step size in parameter space.

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Latent Space",
        "japanese_term": "潜在空間",
        "concept_content": """Latent Space (潜在空間 - せんざいくうかん)

A compressed representation space where similar data points are close together. 
Used in autoencoders, GANs, and variational models.

Properties:
- Dimensionality Reduction (次元削減): Maps high-dimensional data to lower dimensions
- Feature Learning (特徴学習): Learns meaningful representations
- Interpolation (補間): Smooth transitions between data points

Applications: Image generation, style transfer, anomaly detection

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Neural Network",
        "japanese_term": "ニューラルネットワーク",
        "concept_content": """Neural Network (ニューラルネットワーク)

A computing system inspired by biological neural networks. Consists of interconnected nodes (neurons) organized in layers.

Architecture:
- Input Layer (入力層): Receives data
- Hidden Layers (隠れ層): Process information
- Output Layer (出力層): Produces predictions

Activation Functions (活性化関数): Introduce non-linearity (ReLU, Sigmoid, Tanh)

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Backpropagation",
        "japanese_term": "誤差逆伝播法",
        "concept_content": """Backpropagation (誤差逆伝播法 - ごさぎゃくでんぱほう)

Algorithm for training neural networks by propagating errors backward through the network.

Process:
1. Forward Pass (順伝播): Compute predictions
2. Calculate Loss (損失計算): Compare predictions to targets
3. Backward Pass (逆伝播): Compute gradients
4. Update Weights (重み更新): Adjust parameters using gradients

Chain Rule (連鎖律): Mathematical foundation for computing gradients

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Convolutional Neural Network",
        "japanese_term": "畳み込みニューラルネットワーク",
        "concept_content": """Convolutional Neural Network (畳み込みニューラルネットワーク - たたみこみニューラルネットワーク)

Deep learning architecture designed for processing grid-like data (images, time series).

Key Components:
- Convolutional Layers (畳み込み層): Apply filters to detect features
- Pooling Layers (プーリング層): Reduce spatial dimensions
- Fully Connected Layers (全結合層): Final classification/regression

Applications: Image recognition, computer vision, medical imaging

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Recurrent Neural Network",
        "japanese_term": "再帰型ニューラルネットワーク",
        "concept_content": """Recurrent Neural Network (再帰型ニューラルネットワーク - さいきがたニューラルネットワーク)

Neural network architecture with feedback connections, designed for sequential data.

Variants:
- LSTM (Long Short-Term Memory): 長短期記憶ネットワーク
- GRU (Gated Recurrent Unit): ゲート付き回帰ユニット
- Bidirectional RNN (双方向RNN): Processes sequences in both directions

Applications: Language modeling, speech recognition, time series prediction

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Generative Adversarial Network",
        "japanese_term": "敵対的生成ネットワーク",
        "concept_content": """Generative Adversarial Network (敵対的生成ネットワーク - てきたいてきせいせいネットワーク)

Two neural networks competing: Generator (生成器) creates fake data, Discriminator (識別器) distinguishes real from fake.

Training Process:
- Generator learns to fool discriminator
- Discriminator learns to detect fakes
- Adversarial training improves both

Applications: Image generation, style transfer, data augmentation

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Attention Mechanism",
        "japanese_term": "アテンション機構",
        "concept_content": """Attention Mechanism (アテンション機構)

Allows models to focus on relevant parts of input when making predictions.

Types:
- Self-Attention (セルフアテンション): Attention within same sequence
- Cross-Attention (クロスアテンション): Attention between different sequences
- Multi-Head Attention (マルチヘッドアテンション): Multiple attention heads in parallel

Key Innovation: Enables parallel processing and long-range dependencies

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Reinforcement Learning",
        "japanese_term": "強化学習",
        "concept_content": """Reinforcement Learning (強化学習 - きょうかがくしゅう)

Machine learning paradigm where agents learn by interacting with environment through rewards and penalties.

Components:
- Agent (エージェント): Learning entity
- Environment (環境): External system
- Reward Signal (報酬信号): Feedback mechanism
- Policy (方策): Strategy for action selection

Applications: Game playing, robotics, autonomous systems

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Transfer Learning",
        "japanese_term": "転移学習",
        "concept_content": """Transfer Learning (転移学習 - てんいがくしゅう)

Technique of reusing a pre-trained model on a new, related task.

Process:
1. Pre-train on large dataset (事前学習)
2. Fine-tune on target task (ファインチューニング)
3. Transfer knowledge (知識転移)

Benefits: Faster training, better performance with less data

Applications: Computer vision, NLP, domain adaptation

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Hyperparameter Tuning",
        "japanese_term": "ハイパーパラメータ調整",
        "concept_content": """Hyperparameter Tuning (ハイパーパラメータ調整)

Process of finding optimal hyperparameters (parameters set before training).

Methods:
- Grid Search (グリッドサーチ): Exhaustive search over parameter grid
- Random Search (ランダムサーチ): Random sampling of parameters
- Bayesian Optimization (ベイズ最適化): Probabilistic model-based optimization

Common Hyperparameters: Learning rate, batch size, network depth

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Overfitting",
        "japanese_term": "過学習",
        "concept_content": """Overfitting (過学習 - かがくしゅう)

When a model learns training data too well, including noise, and fails to generalize to new data.

Symptoms:
- High training accuracy, low validation accuracy
- Large gap between train and validation loss

Solutions:
- Regularization (正則化): L1/L2 penalties
- Dropout (ドロップアウト): Randomly disable neurons
- Early Stopping (早期停止): Stop training when validation loss increases
- Data Augmentation (データ拡張): Increase dataset diversity

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Batch Normalization",
        "japanese_term": "バッチ正規化",
        "concept_content": """Batch Normalization (バッチ正規化)

Technique to normalize inputs of each layer by adjusting and scaling activations.

Benefits:
- Faster training convergence
- Allows higher learning rates
- Reduces internal covariate shift
- Acts as regularization

Process: Normalize → Scale → Shift using learnable parameters

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Word Embedding",
        "japanese_term": "単語埋め込み",
        "concept_content": """Word Embedding (単語埋め込み - たんごうめこみ)

Dense vector representations of words that capture semantic relationships.

Methods:
- Word2Vec (ワードツーベック): Predicts context or target words
- GloVe (グローブ): Global vectors from word co-occurrence
- FastText (ファストテキスト): Character-level n-grams

Properties: Similar words have similar vectors, arithmetic operations capture relationships

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Feature Engineering",
        "japanese_term": "特徴量エンジニアリング",
        "concept_content": """Feature Engineering (特徴量エンジニアリング)

Process of selecting, modifying, or creating features to improve model performance.

Techniques:
- Feature Selection (特徴選択): Choose relevant features
- Feature Transformation (特徴変換): Normalize, scale, encode
- Feature Creation (特徴作成): Combine or derive new features
- Dimensionality Reduction (次元削減): PCA, t-SNE

Importance: Often more impactful than algorithm choice

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Ensemble Learning",
        "japanese_term": "アンサンブル学習",
        "concept_content": """Ensemble Learning (アンサンブル学習)

Combining multiple models to improve predictions beyond individual models.

Methods:
- Bagging (バギング): Bootstrap aggregating (Random Forest)
- Boosting (ブースティング): Sequential model training (AdaBoost, XGBoost)
- Stacking (スタッキング): Meta-learner combines base models
- Voting (投票): Majority or weighted voting

Principle: Wisdom of the crowd - multiple weak learners → strong learner

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Cross-Validation",
        "japanese_term": "交差検証",
        "concept_content": """Cross-Validation (交差検証 - こうさけんしょう)

Resampling technique to assess model performance and prevent overfitting.

Types:
- K-Fold (K分割): Split data into k folds, train on k-1, test on 1
- Stratified K-Fold (層化K分割): Maintains class distribution
- Leave-One-Out (一抜き交差検証): Each sample as test set once
- Time Series CV (時系列交差検証): Respects temporal order

Purpose: Better estimate of model generalization

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Activation Function",
        "japanese_term": "活性化関数",
        "concept_content": """Activation Function (活性化関数 - かっせいかかんすう)

Non-linear function applied to neuron outputs to introduce non-linearity into neural networks.

Common Functions:
- ReLU (Rectified Linear Unit): 正規化線形ユニット - f(x) = max(0, x)
- Sigmoid (シグモイド): S-shaped curve, outputs 0-1
- Tanh (タンジェント双曲線): Outputs -1 to 1
- Softmax (ソフトマックス): Multi-class probability distribution

Purpose: Enables networks to learn complex patterns

Difficulty: Advanced
Class: Tech""",
    },
    {
        "concept_title": "Loss Function",
        "japanese_term": "損失関数",
        "concept_content": """Loss Function (損失関数 - そんしつかんすう)

Function that measures the difference between predicted and actual values.

Types:
- Mean Squared Error (平均二乗誤差): For regression
- Cross-Entropy Loss (交差エントロピー損失): For classification
- Binary Cross-Entropy (二値交差エントロピー): For binary classification
- Hinge Loss (ヒンジ損失): For SVM

Purpose: Guides optimization during training

Difficulty: Advanced
Class: Tech""",
    },
]


def seed_ai_ml_terms():
    """Seed the knowledge_base with 20 advanced AI/ML terms."""
    print("=" * 60)
    print("🤖 Seeding Advanced AI/ML Terms")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    db: Session = SessionLocal()
    try:
        seeded_count = 0
        updated_count = 0
        
        for term_data in AI_ML_TERMS:
            # Check if entry already exists
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.concept_title == term_data["concept_title"],
                KnowledgeBase.category == "tech"
            ).first()
            
            if existing:
                # Update existing entry
                existing.concept_content = term_data["concept_content"]
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
                print(f"✅ Updated: {term_data['concept_title']} ({term_data['japanese_term']})")
            else:
                # Create new entry
                kb_entry = KnowledgeBase(
                    source_file="ai_ml_advanced_terms",
                    concept_title=term_data["concept_title"],
                    concept_content=term_data["concept_content"],
                    language="en",  # English with Japanese technical terms
                    category="tech",
                    page_number=None,
                )
                db.add(kb_entry)
                seeded_count += 1
                print(f"✅ Added: {term_data['concept_title']} ({term_data['japanese_term']})")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"🎉 Seeding Complete!")
        print(f"   Added: {seeded_count} entries")
        print(f"   Updated: {updated_count} entries")
        print(f"   Total: {len(AI_ML_TERMS)} AI/ML terms")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding AI/ML terms: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_ai_ml_terms()


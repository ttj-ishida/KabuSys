# KabuSys

日本株自動売買システム（KabuSys）の軽量な骨格リポジトリです。  
このリポジトリは自動売買システムを構成する主要コンポーネント（データ取得、売買戦略、注文発行、監視）をモジュール単位で分離したテンプレートを提供します。現状は基本的なパッケージ構成のみが含まれ、実装は各モジュールに追加していく前提です。

バージョン: 0.1.0

---

## 機能一覧（想定・テンプレート）

- モジュール分割による拡張しやすい構成
  - data: 市場データの取得・加工
  - strategy: 売買アルゴリズム（シグナル生成）
  - execution: 注文の発行・注文管理（ブローカーAPIとの接続）
  - monitoring: ログ・メトリクス・稼働監視
- パッケージとして簡単にインポート可能（拡張点を明確にするテンプレート）
- 開発者が独自の戦略や実行モジュールを追加できる骨組み

※ 現在のリポジトリはテンプレート（モジュール初期化のみ）です。実際のデータ取得や注文処理の実装は含まれていません。

---

## セットアップ手順

前提
- Python 3.8+ を推奨

1. リポジトリをクローン
   ```bash
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. インストール（開発中は編集を反映するため editable install 推奨）
   - 要件があれば `requirements.txt` を作成してから以下を実行してください。
   ```bash
   pip install -e .
   # または、依存パッケージがある場合
   pip install -r requirements.txt
   pip install -e .
   ```

4. 動作確認（パッケージがインポートできるか）
   ```bash
   python -c "import kabusys; print(kabusys.__version__)"
   ```

---

## 使い方（開発者向けの基本例）

このパッケージはモジュール単位で拡張して使います。現状は各サブパッケージが空のイニシャライザを持つのみです。以下は各モジュールにクラスや関数を追加する際の例（サンプル実装）です。

1. 簡単なバージョン確認
   ```python
   import kabusys
   print(kabusys.__version__)  # -> "0.1.0"
   ```

2. 例: strategy モジュールにシンプルな戦略を追加する
   - ファイル: src/kabusys/strategy/simple.py
   ```python
   class SimpleStrategy:
       def __init__(self, window=5):
           self.window = window
           self.prices = []

       def on_new_price(self, price):
           self.prices.append(price)
           if len(self.prices) > self.window:
               self.prices.pop(0)
           return self.generate_signal()

       def generate_signal(self):
           if len(self.prices) < self.window:
               return None
           # 単純移動平均を使った例（単純なダミー）
           sma = sum(self.prices) / len(self.prices)
           if self.prices[-1] > sma:
               return "BUY"
           elif self.prices[-1] < sma:
               return "SELL"
           return None
   ```

3. 例: execution モジュールに注文発行のダミーを追加
   - ファイル: src/kabusys/execution/mock.py
   ```python
   class MockExecutor:
       def send_order(self, symbol, side, qty):
           # 実運用時は証券会社APIを呼ぶ実装に差し替える
           print(f"Send order: {symbol} {side} {qty}")
           return {"order_id": "mock-123"}
   ```

4. モニタリングの追加（ログやメトリクス）
   - ファイル: src/kabusys/monitoring/logging.py
   ```python
   import logging
   logger = logging.getLogger("kabusys")
   logger.setLevel(logging.INFO)
   ```

これらを組み合わせて、データ取得 -> 戦略 -> 注文発行 のワークフローを作成します。

---

## 開発の進め方（推奨）

- data:
  - 市場データ取得（REST/WebSocket）、パース、キャッシュ機構を実装
  - テスト用にモックデータ生成モジュールを用意
- strategy:
  - Strategy 抽象クラスを定義し、状態管理（ポジション、注文中フラグ等）を標準化
  - 単体テストでロジックを検証
- execution:
  - ブローカー（例: kabu.com API）との接続層を分離
  - リトライ、注文ステータスの同期、エラーハンドリング実装
- monitoring:
  - ロギング、メトリクス（Prometheus 等）、アラート発行を組み込む

テスト・CIも早めに整備すると安全です（ユニットテスト、統合テスト、シミュレーション実行など）。

---

## ディレクトリ構成

現在のリポジトリの主要ファイル/ディレクトリ構成は以下の通りです。

```
.
├── src/
│   └── kabusys/
│       ├── __init__.py        # パッケージメタ情報（version 等）
│       ├── data/
│       │   └── __init__.py
│       ├── strategy/
│       │   └── __init__.py
│       ├── execution/
│       │   └── __init__.py
│       └── monitoring/
│           └── __init__.py
└── README.md
```

- 各サブディレクトリに実装ファイル（.py）を追加して機能を拡張してください。

---

## 注意事項 / ライセンス

- このリポジトリはテンプレート/骨組みです。実取引で使う前に十分なテストと安全対策（リスク管理、接続の冗長化、認証情報の管理など）を行ってください。
- ライセンスや貢献ガイドラインが必要であれば、別途 LICENSE / CONTRIBUTING ファイルを追加してください。

---

ご要望があれば、各モジュールの推奨インターフェース（Strategy base class、Executor interface、DataFetcher など）のテンプレート実装を作成します。どの機能から実装したいか教えてください。
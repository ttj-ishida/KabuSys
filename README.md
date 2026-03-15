# KabuSys

KabuSys は日本株の自動売買システム向けの軽量な骨組み（スケルトン）ライブラリです。戦略の実装（strategy）、データ取り込み（data）、売買実行（execution）、監視・ログ（monitoring）といった責務を分離した構成を提供します。現在は基本的なパッケージ構成のみを含む初期バージョン（0.1.0）です。

バージョン: 0.1.0

---

## 機能一覧

- プロジェクト骨組み（パッケージ分割）
  - data: 市場データの取得・前処理を実装するための領域
  - strategy: 取引戦略（シグナル生成）を実装する領域
  - execution: ブローカー／API を使った約定処理を実装する領域
  - monitoring: ログやモニタリング／アラートを実装する領域
- 軽量で拡張しやすいディレクトリ構成（src レイアウト）
- パッケージ情報（__version__）の提供

> 注: 本リポジトリはシステムの骨組みを提供するテンプレートです。実運用に使う場合は、各モジュールに具体的な実装（API キー管理、注文ロジック、リスク管理、例外処理、単体テストなど）を追加してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨（プロジェクト要件に合わせて変更してください）

1. リポジトリをクローン
   ```
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化（例: venv）
   - Unix / macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - 本テンプレートではデフォルトの依存関係ファイルは含まれていません。必要なパッケージがある場合は `requirements.txt` や `pyproject.toml` を追加してください。
   - パッケージング用ファイル（`setup.py` / `pyproject.toml`）がある場合:
     ```
     python -m pip install -e .
     ```
   - まだパッケージ化していない開発段階では、プロジェクトルートを PYTHONPATH に追加するか、直接 src ディレクトリを参照して利用できます。

---

## 使い方（簡易）

パッケージの基本的な利用例（インポートやバージョン確認）:

```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

各サブパッケージは以下の責務を担います。実装例はプロジェクト固有に作成してください。

- data
  - 市場データの取得（API、CSV、DB）
  - データ前処理（欠損、リサンプリング）
- strategy
  - シグナル生成（例: 移動平均クロス、RSI、ボラティリティなど）
  - ポジション管理ロジック
- execution
  - 注文送信（成行、指値）
  - 注文状態管理（約定確認、キャンセル）
  - ブローカー API ラッパー
- monitoring
  - ログ出力、メトリクス収集
  - アラート（メール／Slack など）

簡単なフロー（擬似コード）:

```python
from kabusys.data import MarketDataLoader    # 実装はユーザ次第
from kabusys.strategy import MyStrategy      # ユーザ実装
from kabusys.execution import BrokerClient   # ブローカー実装
from kabusys.monitoring import Monitor       # 監視用実装

# データ取得
data = MarketDataLoader(...).load(symbol="7203")

# シグナル作成
strategy = MyStrategy(...)
signal = strategy.generate(data)

# 注文実行
client = BrokerClient(api_key="...", secret="...")
if signal == "BUY":
    client.place_order(symbol="7203", side="BUY", qty=100)

# 監視・ログ
Monitor().record(...)
```

注意: 上記はあくまでテンプレートの利用イメージです。実際の API 名や引数は実装に合わせて作成してください。

---

## ディレクトリ構成

現在の主要ファイル／ディレクトリ構成:

- src/
  - kabusys/
    - __init__.py                # パッケージヘッダ（バージョン等）
    - data/
      - __init__.py              # データ関連モジュール置き場
    - strategy/
      - __init__.py              # 戦略関連モジュール置き場
    - execution/
      - __init__.py              # 実行（ブローカーラッパー等）置き場
    - monitoring/
      - __init__.py              # 監視・ログ置き場

ファイル例（現状）:
- src/kabusys/__init__.py
  - ドキュメンテーション文字列: "KabuSys - 日本株自動売買システム"
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 開発ガイド（簡易）

- 新しい機能を追加する場合は、該当サブパッケージ配下にモジュールを作成してください（例: src/kabusys/strategy/moving_average.py）。
- 単体テストや CI を導入することを推奨します（pytest / GitHub Actions など）。
- 機密情報（API キー等）はソース管理に含めず、環境変数やシークレット管理を利用してください。
- 実運用では注文失敗時の再試行、レート制限、スリッページ、例外処理、ロギング・監査トレイルなどを必ず実装してください。

---

## 付記

- このプロジェクトはサンプル／テンプレートです。実際のマネーを使う運用を行う前に、十分なテストとリスク評価を行ってください。
- 貢献や改善提案は Pull Request / Issue にて歓迎します。

--- 

必要があれば README の翻訳（英語版）や、具体的なサンプル実装（サンプル戦略、ブローカーラッパー、データローダー）のテンプレートを作成します。希望があれば教えてください。
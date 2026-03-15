# KabuSys

KabuSys は日本株向けの自動売買システムの骨格（スケルトン）ライブラリです。モジュール化された設計により、データ取得、トレード戦略、注文実行、監視／ログの各コンポーネントを分離して実装できます。現在はパッケージの基本構成（パッケージ名前空間とサブパッケージ）を提供しています。各サブパッケージ内に具体的な実装を追加して拡張してください。

バージョン: 0.1.0

---

## 機能一覧

- プロジェクト構成（モジュール分割）
  - data: 市場データの取得・格納に関する機能
  - strategy: トレーディング戦略の実装箇所
  - execution: 注文送信やブローカー接続の実装箇所
  - monitoring: ログや状態監視、アラートの実装箇所
- 軽量なテンプレートとして利用可能 — 各モジュールに必要なインターフェースを実装して拡張
- Python パッケージとしてインポートして利用可能

> 注意: 現在のリポジトリは枠組み（パッケージ構造）の提供が主目的です。実際の取引ロジックやブローカー接続などは含まれていません。実装と運用は利用者の責任で行ってください。

---

## 要件

- Python 3.8 以上（プロジェクトポリシーに応じて適宜変更してください）
- （任意）ブローカー API、データソース、ロギング等の外部ライブラリ
  - 例: requests、websockets、pandas、numpy、ログライブラリ 等

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. インストール
   - まだ `setup.py` / `pyproject.toml` 等がない場合は、編集してからインストールしてください。
   - 開発中に編集しながら使う場合:
     ```
     pip install -e .
     ```
   - 依存関係がある場合は `requirements.txt` を作成して:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数や認証情報の設定
   - ブローカー API キー等が必要な場合は、環境変数やシークレット管理を使用して設定してください。
   - 例:
     ```
     export KABU_API_KEY="your_api_key"
     export KABU_API_SECRET="your_api_secret"
     ```

---

## 使い方（基本）

まずはパッケージをインポートしてバージョンやモジュール構成を確認します。

```python
import kabusys

print(kabusys.__version__)    # 0.1.0
print(kabusys.__all__)        # ['data', 'strategy', 'execution', 'monitoring']
```

各サブパッケージにはそれぞれの責務に沿った実装を追加します。以下は実装例（雛形）です。

- data: 市場データを取得して整形して返す関数／クラスを実装
```python
# src/kabusys/data/market.py
class MarketDataClient:
    def __init__(self, source_config):
        # データソース初期化（APIキー等）
        pass

    def fetch_ohlcv(self, symbol, interval, limit=100):
        # OHLCVデータを取得して pandas.DataFrame 等で返す
        pass
```

- strategy: データを受け取り売買シグナルを生成する戦略クラスを実装
```python
# src/kabusys/strategy/simple_moving_average.py
class SimpleMAStrategy:
    def __init__(self, short_window=5, long_window=25):
        self.short_window = short_window
        self.long_window = long_window

    def decide(self, market_data):
        # market_data は pandas.DataFrame 等
        # 戦略ロジックを実装し、注文オブジェクト（辞書など）を返す
        # 例: {'action': 'BUY', 'symbol': '7203', 'qty': 100}
        pass
```

- execution: 戦略の出力を受け取り、実際に注文を送信するクラスを実装
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def __init__(self, api_client):
        self.api_client = api_client

    def send_order(self, order):
        # ブローカー API へ注文を送信
        # 例: 成功/失敗のレスポンスを返す
        pass
```

- monitoring: ログ出力やメトリクス、アラートを処理
```python
# src/kabusys/monitoring/logger.py
import logging

logger = logging.getLogger("kabusys")
logger.setLevel(logging.INFO)
# ハンドラを追加して利用
```

ワークフロー例（擬似コード）:
```python
# main.py
from kabusys.data.market import MarketDataClient
from kabusys.strategy.simple_moving_average import SimpleMAStrategy
from kabusys.execution.client import ExecutionClient
from kabusys.monitoring.logger import logger

data_client = MarketDataClient(config)
strategy = SimpleMAStrategy()
exec_client = ExecutionClient(api_client)

market_data = data_client.fetch_ohlcv('7203', '1d')
order = strategy.decide(market_data)
if order:
    result = exec_client.send_order(order)
    logger.info(result)
```

---

## ディレクトリ構成

現状の最小構成は以下の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージ初期化、__version__ を定義
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

開発時は各サブパッケージ内にモジュールファイル（例: market.py, simple_moving_average.py, client.py, logger.py など）を追加して実装してください。

---

## 開発・貢献

- コードフォーマット、型チェック（mypy）、テスト（pytest）などの開発ツールを導入することを推奨します。
- 実際の資金を用いた運用を行う前に、バックテストとペーパートレード環境で十分に検証してください。
- セキュリティ（APIキー管理、例外処理）、健全性チェック（注文サイズ、最大損失制限）、レート制限対策などは各自で確実に実装してください。

---

## ライセンス / 連絡先

このリポジトリのライセンスや連絡先情報はリポジトリに応じて追加してください。プロジェクトの公開・共有前にライセンスを明示することを推奨します。

---

以上。必要があれば README の内容を実装状況に合わせて更新します。特定のサブパッケージにサンプル実装を追加するリクエストがあれば、雛形コードを作成します。
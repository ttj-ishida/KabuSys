# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。現状は最小限のパッケージ構成のみを含み、データ取得、ストラテジー、注文実行、監視の各コンポーネントを実装・拡張するための雛形として設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは、以下の4つの主要コンポーネントを分離したパッケージ構成を提供します。

- data: 市場データの取得や整形を担当するモジュール群
- strategy: 売買シグナル（戦略）を実装する場所
- execution: ブローカー／取引所とのやり取り、注文送信を行う部分
- monitoring: ログ記録、メトリクス、アラートなどの監視機能

現時点ではこれらは空のサブパッケージとして定義されており、各領域の実装を追加するためのベースとなります。

---

## 機能一覧（設計上の想定）

この骨組みに実装すると想定される機能例を列挙します（現時点で未実装・拡張が必要です）。

- 市場データ取得
  - 株価や板情報の取得
  - CSVやデータベースへの保存/読み込み
- ストラテジー
  - シグナル生成（指標やルールベース、機械学習など）
  - バックテスト用の簡易フレームワーク
- 実行（Execution）
  - 注文作成、送信、キャンセル
  - 注文状態管理（未約定、約定、キャンセルなど）
- 監視（Monitoring）
  - ログ、取引履歴の記録
  - リアルタイム監視・アラート（メール/Slackなど）
  - メトリクス集計（損益、ドローダウン等）

---

## セットアップ手順

まずはローカルで開発するための基本手順です。プロジェクトに `pyproject.toml` / `setup.py` / `requirements.txt` が存在しない場合は、必要に応じて追加してください。

前提
- Python 3.8 以上を推奨

手順例:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発用にパッケージをインストール（editable）
   - 既に pyproject.toml / setup.py があれば:
     ```
     pip install -e .
     ```
   - 依存パッケージがある場合は requirements.txt を用意して:
     ```
     pip install -r requirements.txt
     ```

4. インストール確認
   ```
   python -c "import kabusys; print(kabusys.__version__)"
   ```

注意: 現状はパッケージのスケルトンのみを含むため、実際の外部API連携や取引機能を動作させるには追加実装と依存ライブラリの導入が必要です。

---

## 使い方（開発者向けガイド）

現在のパッケージはモジュールの入れ物を提供しています。実装例や推奨インターフェースを下記に示します。これらはあくまで一例ですので、プロジェクトの方針に合わせて設計してください。

基本的なインポート:
```python
import kabusys
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring

print(kabusys.__version__)  # "0.1.0"
```

モジュール設計のサンプル（擬似コード）:

- data: 市場データフェッチャー
```python
# src/kabusys/data/market.py
class MarketDataFetcher:
    def __init__(self, source_config):
        pass

    def fetch_latest(self, symbol):
        # 最新のティック/板/終値などを返す
        return {}
```

- strategy: シンプル戦略クラス
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def generate_signals(self, market_snapshot):
        # シグナルのリストを返す（例: [{'symbol': '7203', 'side': 'BUY', 'qty': 100}])
        return []
```

- execution: 注文実行インターフェース
```python
# src/kabusys/execution/broker.py
class BrokerClient:
    def place_order(self, order):
        # 注文を送信し、応答を返す
        return {"order_id": "12345"}
```

- monitoring: ロギング・モニタ
```python
# src/kabusys/monitoring/logging.py
class Monitor:
    def record_trade(self, trade_info):
        pass

    def alert(self, message):
        pass
```

運用オーケストレーション（擬似スクリプト）:
```python
from kabusys.data.market import MarketDataFetcher
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.broker import BrokerClient
from kabusys.monitoring.logging import Monitor
import time

md = MarketDataFetcher(config)
st = SimpleStrategy()
bc = BrokerClient(api_key)
mon = Monitor()

while True:
    snapshot = md.fetch_latest("7203")
    signals = st.generate_signals(snapshot)
    for s in signals:
        res = bc.place_order(s)
        mon.record_trade(res)
    time.sleep(1)
```

注意: 上記はインターフェース例です。実際の取引システムを作る際はエラー処理、リトライ、レート制限、資金管理、セキュリティ（APIキーの安全な管理）等を必ず実装してください。

---

## ディレクトリ構成

現在のリポジトリ構成（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py               # パッケージのメタ情報（バージョン、サブパッケージ公開）
    - data/
      - __init__.py
      # データ取得関連モジュールを追加
    - strategy/
      - __init__.py
      # 戦略実装を追加
    - execution/
      - __init__.py
      # 注文実行/ブローカ連携を追加
    - monitoring/
      - __init__.py
      # ログ・メトリクス関連を追加

上記は初期状態のスケルトンです。各サブパッケージ内にモジュール（.py）を追加して機能を実装してください。

---

## 開発・貢献について

- 新しい機能やバグ修正はブランチを切ってプルリクエストを送ってください。
- 重要な変更（APIの破壊的変更など）はREADMEおよび必要に応じてCHANGELOGで明示してください。
- テストは各機能追加時に pytest 等で追加してください（現状テストはありません）。
- セキュリティに関わる情報（APIキー等）はリポジトリに含めないでください。環境変数やシークレットマネージャを使用してください。

---

## 注意事項（重要）

- 本リポジトリは「売買の実行」を想定しています。実際の資金を用いた取引を行う場合は、各種規約や法令、取引所／ブローカーのルールに従ってください。
- 実運用前に十分なバックテスト・ペーパートレードを行い、リスク管理ルールを確立してください。
- ここに示したコード例は簡易的なものであり、商用運用にそのまま使えるものではありません。

---

README の改善案や追加したいサンプル実装（例: 市場データ取得モジュール、ブローカーラッパ、簡易ストラテジー、CI設定、テストケース等）があれば、要件に沿って具体的なテンプレートや実装例を提供します。どの部分から拡張したいか教えてください。
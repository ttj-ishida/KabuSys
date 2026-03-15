# KabuSys

KabuSys は日本株の自動売買システムの骨組み（雛形）です。  
データ取得、売買戦略、注文実行、監視（ログ／アラート）を分離したモジュール構成になっており、独自のアルゴリズムやブローカー連携を組み込んで拡張することを想定しています。

バージョン: 0.1.0

---

## 機能一覧（概要）
- モジュール分割されたパッケージ構造
  - data: 市場データ取得用（履歴・リアルタイム）の処理を実装
  - strategy: 売買戦略ロジックを実装
  - execution: ブローカー API 等への注文送信を実装
  - monitoring: ログ収集、状態監視、アラートを実装
- それぞれの領域ごとに責務を分離しているため、個別に差し替え／テストが可能
- パッケージ化済み（src 配下のパッケージ）

※ 現在は骨組みのみで、個別実装（API クライアントや具体的な戦略ロジック）は含まれていません。拡張して利用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. Python 環境の準備（推奨: 仮想環境）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール  
   このリポジトリに requirements.txt / pyproject.toml が無い場合は、プロジェクトに必要なパッケージを適宜インストールしてください（例: requests, pandas, websocket-client, ccxt 等）。
   例:
   ```
   pip install requests pandas
   ```

   開発中にパッケージを編集して動作確認したい場合は、パッケージを editable インストールします（プロジェクトに setup.py か pyproject.toml があることが前提）。
   ```
   pip install -e .
   ```

4. ソースを直接参照する場合（簡易）
   - PYTHONPATH に `src` を追加するか、作業ディレクトリから実行してください。
   ```
   export PYTHONPATH=$PWD/src:$PYTHONPATH  # macOS / Linux
   set PYTHONPATH=%CD%\src;%PYTHONPATH%    # Windows（PowerShell では異なる）
   ```

---

## 使い方（例・テンプレート）

以下は各モジュールに実装を追加していく際の簡単なテンプレート例です。現状パッケージは空のサブパッケージのみ提供しているため、まずはインターフェース（クラス／関数）を定めて実装してください。

例: データ取得クラス（src/kabusys/data/fetcher.py）
```python
# src/kabusys/data/fetcher.py
class DataFetcher:
    def fetch_history(self, symbol: str, start: str, end: str):
        """過去データを取得して pandas.DataFrame 等で返す"""
        raise NotImplementedError

    def subscribe_realtime(self, symbols, callback):
        """リアルタイムデータ購読。コールバックでデータを受け取る"""
        raise NotImplementedError
```

例: 戦略クラス（src/kabusys/strategy/simple.py）
```python
# src/kabusys/strategy/simple.py
class Strategy:
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher

    def on_tick(self, tick):
        """ティック受信時に判断し、注文を返す/もしくは Executor を呼ぶ"""
        # return {"symbol": "7203", "side": "BUY", "size": 100}
        raise NotImplementedError
```

例: 注文実行クラス（src/kabusys/execution/broker.py）
```python
# src/kabusys/execution/broker.py
class Executor:
    def place_order(self, order):
        """ブローカー API に注文を投げる"""
        raise NotImplementedError

    def cancel_order(self, order_id):
        raise NotImplementedError
```

例: 監視（ログ／アラート）（src/kabusys/monitoring/logger.py）
```python
# src/kabusys/monitoring/logger.py
class Monitor:
    def log(self, message: str):
        """ログ出力"""
        print(message)

    def alert(self, subject: str, message: str):
        """アラート送信（メール / Slack 等）"""
        raise NotImplementedError
```

簡易的な実行フロー（擬似コード）
```python
from kabusys.data.fetcher import DataFetcher
from kabusys.strategy.simple import Strategy
from kabusys.execution.broker import Executor
from kabusys.monitoring.logger import Monitor

data = DataFetcher(...)
strategy = Strategy(data)
executor = Executor(...)
monitor = Monitor()

# リアルタイム購読
data.subscribe_realtime(["7203"], lambda tick: handle_tick(tick))

def handle_tick(tick):
    order = strategy.on_tick(tick)
    if order:
        result = executor.place_order(order)
        monitor.log(f"order result: {result}")
```

---

## ディレクトリ構成

現在のコードベース（主要ファイル）は以下の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ定義（バージョン等）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

現状はサブパッケージの雛形だけが存在します。各サブパッケージに実装ファイル（fetcher.py、strategy 実装、executor 実装、logger/alerter など）を追加していくことを想定しています。

---

## 開発・拡張のポイント
- 各レイヤーは疎結合にする（例: Strategy は Executor を直接操作せず、注文情報を返す／イベントとして発行する）。
- テストを書きやすくするために、外部 API は接口（抽象クラス）で分離しモック可能にする。
- 重要な処理（注文実行など）は冪等性やエラー処理、リトライ、ログ記録を必ず設ける。
- 実運用時はログやアラート、監査トレイル（何をいつ発注したか）を保存すること。

---

## 参考・次のステップ
- 各モジュールに具体的な実装を追加する（例: kabu.com API、証券会社 API、CSV や DB によるデータ保存など）。
- CI / テスト（pytest）を導入する。
- 実運用前に十分なバックテストとペーパートレード（テスト環境）での検証を行う。

---

必要であれば、README に実際の依存関係や具体的な実装例（kabu.com API を使った DataFetcher / Executor のサンプルコード）を追加します。どのブローカー／データソースを想定しているか教えてください。
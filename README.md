# KabuSys

KabuSys は日本株の自動売買（アルゴリズムトレーディング）システムの骨組みを提供するPythonパッケージです。データ取得、戦略（ストラテジー）、注文実行、監視（モニタリング）をそれぞれ分離したモジュール構成になっており、独自のロジックや外部API接続を差し替えて利用できます。

バージョン: 0.1.0

---

## 主な特徴

- モジュール化されたパッケージ構成（data / strategy / execution / monitoring）
- 最小限の骨組みを提供し、ユーザが自分の戦略や実行ロジックを実装可能
- テストや開発を想定したシンプルな構造

---

## 機能一覧（現状の役割）

- data: 市場データの取得・整形を担当するモジュール（株価、板情報など）
- strategy: 売買判断のロジックを実装するモジュール
- execution: 注文送信や約定処理を行うモジュール（証券会社APIラッパー等）
- monitoring: ログ記録やモニタリング・アラートを行うモジュール

> 注意: このリポジトリは「骨組み（スケルトン）」です。各モジュールの具体的な実装（APIクライアントや取引ロジック）は含まれていません。実運用前に十分な実装とテストが必要です。

---

## 前提条件

- Python 3.8+
- （任意）仮想環境（venv, virtualenv, pyenv など）
- 実行に必要な外部ライブラリがある場合は、各自の実装に応じて `requirements.txt` を作成してください

---

## セットアップ手順

1. リポジトリをクローンする
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・アクティベート（推奨）
   - Unix / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージを開発モードでインストール
   ```
   pip install -e src
   ```
   （プロジェクトルートが `src` レイアウトであることを想定）

4. 必要な依存パッケージをインストール
   - このスケルトンには依存パッケージは同梱していません。外部APIやデータ処理に必要なライブラリ（requests, websockets, pandas など）を `pip install` で追加してください。

---

## 使い方（基本）

パッケージをインポートしてバージョンを確認する簡単な例:
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

典型的な自動売買ワークフロー（疑似コード）:
1. data モジュールで市場データを取得
2. strategy モジュールでシグナル（買い/売り/ホールド）を生成
3. execution モジュールで注文を送信（成行/指値など）
4. monitoring モジュールでログ、メトリクス、アラートを出力

サンプルの簡易スケルトン:
```python
# data/my_data_provider.py
class DataProvider:
    def get_latest_price(self, symbol):
        # 実際はAPI呼び出しなど
        return 1000

# strategy/my_strategy.py
class MyStrategy:
    def decide(self, price):
        # 単純な閾値ロジックの例
        if price < 950:
            return "BUY"
        elif price > 1050:
            return "SELL"
        else:
            return "HOLD"

# execution/my_executor.py
class Executor:
    def send_order(self, symbol, side, quantity):
        # 証券口座APIに注文を出す実装が必要
        return {"order_id": "abc123", "status": "SENT"}

# monitoring/my_monitor.py
class Monitor:
    def log(self, message):
        print(message)

# main loop
from data.my_data_provider import DataProvider
from strategy.my_strategy import MyStrategy
from execution.my_executor import Executor
from monitoring.my_monitor import Monitor

dp = DataProvider()
st = MyStrategy()
ex = Executor()
mo = Monitor()

symbol = "7203"  # 例: トヨタ自動車の銘柄コード
price = dp.get_latest_price(symbol)
signal = st.decide(price)
if signal in ("BUY", "SELL"):
    order = ex.send_order(symbol, side=signal, quantity=100)
    mo.log(f"注文: {order}")
```

---

## 拡張ガイド（各モジュールの推奨インタフェース）

- data
  - 役割: リアルタイム/履歴データ取得、前処理
  - 推奨メソッド: get_latest_price(symbol), get_orderbook(symbol), stream_ticks(...)

- strategy
  - 役割: データを受け取り売買シグナルを出す
  - 推奨メソッド: decide(market_data) -> {"action": "BUY"/"SELL"/"HOLD", "size": int, ...}

- execution
  - 役割: 証券会社APIとの通信（注文送信、注文状況確認、キャンセル）
  - 推奨メソッド: send_order(symbol, side, size, price=None), get_order_status(order_id), cancel_order(order_id)

- monitoring
  - 役割: ログ、メトリクス、アラート（メール/Slack等）
  - 推奨メソッド: log(msg), alert(level, msg), record_metric(name, value)

これらはあくまで推奨インタフェースです。運用やAPI仕様に合わせて設計を変更してください。

---

## ディレクトリ構成

現状のファイル構成は以下の通りです:

- src/
  - kabusys/
    - __init__.py              # パッケージ定義（__version__ = "0.1.0"）
    - data/
      - __init__.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

サンプル（拡張後）の推奨構成例:
- src/
  - kabusys/
    - data/
      - __init__.py
      - providers.py
    - strategy/
      - __init__.py
      - base.py
      - implementations/
    - execution/
      - __init__.py
      - broker_adapters.py
    - monitoring/
      - __init__.py
      - logger.py
    - utils/
    - config.py

---

## テスト・デバッグ

- ユニットテストは実装に合わせて pytest などで追加してください。
- 実運用前にペーパートレード環境やレコード再生（バックテスト）で十分に検証してください。
- 注文実行部分は特にエラー処理（ネットワーク障害、APIのレート制限、部分約定など）を丁寧に実装してください。

---

## 貢献方法

1. Issue を立てて改善点や提案を共有してください。
2. フォークしてブランチを作成、変更を加えたら Pull Request を送ってください。
3. PR には目的、変更点、動作確認手順を明記してください。

---

## ライセンス

このリポジトリにライセンス情報が含まれていない場合は、利用・配布する前にライセンスを明示してください。開発・公開する際は適切なライセンス（MIT, Apache2.0 等）を追加することを推奨します。

---

補足:
この README は現在のコードベース（最小スケルトン）に基づいた説明です。実用に供するためには、データ取得・注文実行のための具体的な実装（証券会社APIクレデンシャル管理、エラーハンドリング、ロギング、セキュリティ対策等）が必要です。必要であれば、具体的なサンプル実装（kabuステーション / kabu API 等との連携例）を作成しますので、その旨を教えてください。
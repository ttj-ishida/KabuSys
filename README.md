# KabuSys

KabuSys は日本株の自動売買システムを想定した、シンプルで拡張しやすい Python パッケージの雛形です。データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）の4つの責務をモジュール単位で分離しており、各モジュールを実装・差し替えて利用できます。

バージョン: 0.1.0

---

## 概要

このプロジェクトは、自動売買システムを構築するための基本的なパッケージ構成を提供します。各責務（データ取得、戦略、注文実行、監視）を独立したサブパッケージとして定義しており、自分の取引ロジックやブローカーAPIに合わせて実装を追加していく設計になっています。

目的:
- モジュール化された自動売買アーキテクチャの雛形を提供
- テストしやすく、拡張しやすい構成を促進
- 実際のブローカーAPIやデータソースと結合するための足がかりを提供

---

## 機能一覧（雛形）

- パッケージ化されたモジュール構成
  - data: マーケットデータや履歴データの取得・加工
  - strategy: 売買ロジック（シグナル生成）
  - execution: 注文送信と約定管理（ブローカーAPIとの接続ポイント）
  - monitoring: ログ、メトリクス、アラート等の監視機能
- バージョン情報（`kabusys.__version__`）
- 各モジュールを容易に拡張・差し替え可能な設計

注: 現状は雛形であり、具体的なデータソースやブローカーAPIの実装は含まれていません。これらはプロジェクト用途に合わせて実装してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨（プロジェクトの要件に合わせて変更可）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate        # macOS/Linux
   .venv\Scripts\activate           # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 開発用依存パッケージをインストール（必要なパッケージを requirements.txt に追加してください）
   例（一般的に使われるライブラリ）:
   ```
   pip install -U pip
   pip install pandas numpy requests
   ```
   ※実際に使用するブローカーAPIや WebSocket クライアント等があればここで追加してください（例: websockets, aiohttp など）。

4. パッケージをローカルインストール（編集しながら使う場合は editable インストール）
   ```
   pip install -e src
   ```

5. 動作確認（Python REPL でバージョン表示）
   ```python
   >>> import kabusys
   >>> print(kabusys.__version__)
   0.1.0
   ```

---

## 使い方（基本例・拡張ガイド）

このパッケージはサブパッケージを実装して使います。以下はそれぞれの役割に対する最小の実装例（スケルトン）です。実際のロジックやAPI接続はプロジェクト要件に合わせて実装してください。

例: data モジュールにデータ取得クラスを追加する
```python
# src/kabusys/data/my_data.py
class MarketDataProvider:
    def get_latest_price(self, symbol: str) -> float:
        # 実装: API や CSV 等から価格を取得して返す
        return 100.0
```

例: strategy モジュールに単純な戦略を実装する
```python
# src/kabusys/strategy/simple.py
from kabusys.data.my_data import MarketDataProvider

class SimpleStrategy:
    def __init__(self, data_provider: MarketDataProvider):
        self.data = data_provider

    def decide(self, symbol: str) -> str:
        price = self.data.get_latest_price(symbol)
        # 単純な閾値ロジック
        if price > 110:
            return "SELL"
        elif price < 90:
            return "BUY"
        return "HOLD"
```

例: execution モジュールに注文送信インターフェースを実装する
```python
# src/kabusys/execution/executor.py
class BrokerExecutor:
    def send_order(self, symbol: str, side: str, qty: int):
        # 実装: ブローカーAPIへ注文送信
        print(f"Order: {side} {qty} {symbol}")
```

例: 監視用の簡易 runner
```python
# run.py（プロジェクトルートに置く）
from kabusys.data.my_data import MarketDataProvider
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.executor import BrokerExecutor

data = MarketDataProvider()
strategy = SimpleStrategy(data)
executor = BrokerExecutor()

symbol = "7203"  # 例: トヨタの銘柄コード（仮）
signal = strategy.decide(symbol)
if signal == "BUY":
    executor.send_order(symbol, "BUY", 100)
elif signal == "SELL":
    executor.send_order(symbol, "SELL", 100)
else:
    print("No action")
```

注意点:
- 実際の注文を送信する前に必ずサンドボックス環境やペーパートレードで十分にテストしてください。
- APIキーや認証情報は環境変数や安全なシークレット管理を利用してください（ソースコードに直書きしない）。

---

## ディレクトリ構成

現在のプロジェクト構成（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py                # パッケージのメタ情報（バージョン等）
    - data/
      - __init__.py
      # - my_data.py             # 実装例を追加
    - strategy/
      - __init__.py
      # - simple.py              # 実装例を追加
    - execution/
      - __init__.py
      # - executor.py            # 実装例を追加
    - monitoring/
      - __init__.py
      # - monitor.py             # 実装例を追加

パッケージのルートでのサンプルファイル:
- run.py（例: 上記の実行スクリプトを配置）

---

## 実装ガイドライン / ベストプラクティス（簡潔）

- 責務分離: data, strategy, execution, monitoring を厳密に分けることでテスト・差し替えが容易になります。
- テスト: 重要ロジック（特に strategy）の単体テストを作成し、ヒストリカルデータでバックテストできるようにする。
- 設定とシークレット: APIキーやパスワードは環境変数や設定ファイル（暗号化）で管理する。
- ロギング: 実行履歴やエラーはログとして永続化し、監査可能にする。
- ステージング: 実運用前にサンドボックスやシミュレーションで十分に検証する。

---

この README は雛形プロジェクト向けの説明です。実際の運用に際しては、使用するブローカーの API ドキュメントや法規制（金融商品取引法等）に従って実装と運用を行ってください。
# KabuSys

日本株の自動売買を想定したシンプルなフレームワークです。  
このリポジトリはプロジェクトの骨組み（パッケージ構成）を提供します。各モジュールに実際のロジックを実装して拡張してください。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務ごとにモジュールを分離した設計の自動売買システムの雛形です。

- データ取得（data）
- 売買戦略（strategy）
- 注文実行（execution）
- 監視／ログ（monitoring）

現在のコードベースはパッケージとモジュールの骨組みのみを提供しており、各モジュールの具体的な実装は含まれていません。実装例や拡張のテンプレートを README に記載しています。

---

## 機能一覧（想定）

現状（0.1.0）はインターフェースとパッケージ構成を提供します。将来的に実装することが想定される機能は以下です。

- 株価・板情報・板寄せなどのマーケットデータ取得（data）
- 戦略エンジン（シグナル生成、ポジション管理）（strategy）
- 注文の発注・約定管理（kabuステーション等の API を使った execution）
- ログ・アラート・メトリクス収集・ダッシュボード（monitoring）

---

## セットアップ手順

推奨: Python 3.8 以上

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成（任意だが推奨）
   - macOS / Linux
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発インストール
   ```
   pip install -e .
   ```
   （パッケージの依存がある場合は requirements.txt を追加して `pip install -r requirements.txt` を実行してください）

4. 動作確認
   ```
   python -c "import kabusys; print(kabusys.__version__)"
   ```

---

## 使い方（例・テンプレート）

現状は各モジュールが空のパッケージとして定義されています。以下は各モジュールに実装を追加するときの簡単なテンプレート例です。

- インポートの例
  ```python
  import kabusys
  from kabusys import data, strategy, execution, monitoring
  print(kabusys.__version__)  # 0.1.0
  ```

- data の例（src/kabusys/data/fetcher.py）
  ```python
  class DataFetcher:
      def get_price(self, symbol: str) -> float:
          # 実装: ここで API から価格を取得
          return 1000.0
  ```

- strategy の例（src/kabusys/strategy/simple.py）
  ```python
  class SimpleStrategy:
      def generate_signal(self, price: float) -> str:
          # 実装例: ダミーの売買シグナル
          if price > 1200:
              return "SELL"
          elif price < 800:
              return "BUY"
          return "HOLD"
  ```

- execution の例（src/kabusys/execution/executor.py）
  ```python
  class Executor:
      def send_order(self, symbol: str, side: str, size: int):
          # 実装: ブローカー API に接続して注文を発行
          print(f"Order: {side} {size} {symbol}")
  ```

- monitoring の例（src/kabusys/monitoring/logger.py）
  ```python
  import logging
  logger = logging.getLogger("kabusys")
  logger.setLevel(logging.INFO)

  def report(metric_name: str, value):
      logger.info(f"{metric_name}: {value}")
  ```

統合の例（簡易ワークフロー）
```python
from kabusys.data.fetcher import DataFetcher
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.executor import Executor
from kabusys.monitoring.logger import report

df = DataFetcher()
st = SimpleStrategy()
exe = Executor()

price = df.get_price("7203")  # トヨタ等の銘柄コード
signal = st.generate_signal(price)
if signal in ("BUY", "SELL"):
    exe.send_order("7203", signal, 100)
    report("last_signal", signal)
```

---

## ディレクトリ構成

現在のプロジェクトの最小構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - data/
      - __init__.py
      - (例: fetcher.py)
    - strategy/
      - __init__.py
      - (例: simple.py)
    - execution/
      - __init__.py
      - (例: executor.py)
    - monitoring/
      - __init__.py
      - (例: logger.py)

実際のリポジトリファイル（抜粋）
```
src/kabusys/__init__.py        # パッケージ定義、__version__ 等
src/kabusys/data/__init__.py
src/kabusys/strategy/__init__.py
src/kabusys/execution/__init__.py
src/kabusys/monitoring/__init__.py
```

将来的には以下のようなファイルも含めると良いです:
- setup.cfg / pyproject.toml / setup.py
- requirements.txt
- tests/（ユニットテスト）
- docs/（ドキュメント）

---

## 開発・拡張のヒント

- モジュールごとに責務を明確にし、単体テストを書いておくと安全です。
- 実注文を行う実行モジュールは、テスト用にモック可能なインターフェースを用意してください。
- API キーや認証情報は環境変数やシークレットマネージャーで管理し、ソースに直接書かないでください。
- ロギングやメトリクス収集は monitoring モジュールに集約すると運用が楽になります。

---

もし README に追加したい具体的な実装方針や、使いたい外部 API（例: kabuステーション API）の情報があれば、それに合わせてサンプルやセットアップ手順を追記します。
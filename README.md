# KabuSys

KabuSys は日本株の自動売買システムを想定した軽量なPythonパッケージの土台（テンプレート）です。  
モジュールを分離して設計してあり、データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）をそれぞれ実装・拡張できる構成になっています。

現在のバージョン: 0.1.0

（注）このリポジトリは骨組みのみを含んでおり、各モジュールは実装の拡張が必要です。

## 機能一覧（想定・設計方針）

- モジュール分割による責務の分離
  - data: 市場データの取得・前処理
  - strategy: 売買シグナルの生成（ストラテジー）
  - execution: 注文の発行・管理（API連携）
  - monitoring: ログ、健全性監視、アラート
- 拡張しやすいプラグイン的な構成
- テスト／デプロイの起点として使える軽量テンプレート

## 動作要件

- Python 3.8 以上を推奨
- 必要なライブラリはプロジェクトに依存（現状 requirements は未定義のため、各機能実装時に追加してください）

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（例: venv）
   ```
   python3 -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. パッケージの利用方法（いずれかを選択）
   - 開発中に簡単に利用する（ソース直下の `src` をパスに追加）
     - 実行例:
       ```
       PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
       ```
       Windows (PowerShell):
       ```
       $env:PYTHONPATH="src"; python -c "import kabusys; print(kabusys.__version__)"
       ```
   - または、プロジェクトに packaging（setup.py / pyproject.toml 等）を追加した場合:
     ```
     pip install -e .
     ```

4. 依存ライブラリがある場合は requirements.txt または poetry/poetry.lock 等からインストールしてください（現状は未定義）。

## 使い方（例）

以下は各モジュールを拡張して利用する際の基本的な例です（概念的なサンプル）。

- パッケージのインポートとバージョン確認
  ```python
  from kabusys import __version__ as version
  print("KabuSys version:", version)
  ```

- モジュールの基本的な使い方（拡張例）
  - data: 市場データを提供するクラスを実装
  - strategy: シグナルを生成するクラスを実装
  - execution: 注文を発行するクラスを実装
  - monitoring: ログやアラートを行うクラスを実装

  例（スケルトン）:
  ```python
  # src/kabusys/data/feed.py
  class PriceFeed:
      def get_latest(self, symbol):
          # 実装: API/CSV/DB などから価格を取得
          raise NotImplementedError

  # src/kabusys/strategy/simple.py
  class SimpleStrategy:
      def __init__(self, feed):
          self.feed = feed

      def on_tick(self, symbol):
          price = self.feed.get_latest(symbol)
          # 実装: シグナル生成ロジック
          return {"action": "buy", "qty": 100}  # 例

  # src/kabusys/execution/executor.py
  class Executor:
      def send_order(self, order):
          # 実装: 証券会社APIなどへ注文を投げる
          raise NotImplementedError

  # src/kabusys/monitoring/monitor.py
  class Monitor:
      def report(self, message):
          # 実装: ログ・メール・Slack など
          print(message)
  ```

- 簡単な実行フロー（概念）
  ```python
  from kabusys.data.feed import PriceFeed
  from kabusys.strategy.simple import SimpleStrategy
  from kabusys.execution.executor import Executor
  from kabusys.monitoring.monitor import Monitor

  feed = PriceFeed()
  strat = SimpleStrategy(feed)
  execu = Executor()
  mon = Monitor()

  order = strat.on_tick("7203")  # トヨタ株の例（銘柄コード）
  if order:
      result = execu.send_order(order)
      mon.report(f"Order result: {result}")
  ```

## ディレクトリ構成

現状の最小構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py                # パッケージ初期化、バージョン等
    - data/
      - __init__.py
      (＝市場データ取得周りの実装を配置)
    - strategy/
      - __init__.py
      (＝戦略ロジックを配置)
    - execution/
      - __init__.py
      (＝注文実行ロジックを配置)
    - monitoring/
      - __init__.py
      (＝監視・ログ・アラートを配置)

ファイル例（リポジトリ内）
- src/kabusys/__init__.py
  - パッケージ名とバージョン: __version__ = "0.1.0"
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

（各サブパッケージは現在空で、拡張のためのプレースホルダです）

## 開発・拡張のヒント

- 各モジュールは単一責任の原則に従って実装してください（データ取得は data、売買ロジックは strategy、注文発行は execution、監視は monitoring）。
- テストを追加する場合は tests ディレクトリを作成し、pytest などを導入してください。
- 実運用で証券会社API（例えば kabuステーション API 等）を使う場合は、接続情報や認証情報の管理（環境変数や安全なシークレット管理）に注意してください。
- リアルマネーでの運用前に十分なバックテストとペーパートレードを行ってください。

## 貢献

バグ報告や機能提案は Issue で受け付けます。プルリクエストを歓迎します。  
（コーディング規約、テスト、ドキュメントを含めた PR を推奨します）

---

README はこのプロジェクトの出発点としての説明を提供しています。実装を追加して、目的に合わせて各モジュールを拡張してください。質問や README の改善要望があればお知らせください。
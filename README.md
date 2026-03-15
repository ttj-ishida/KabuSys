# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。モジュール化された設計により、データ取得、売買戦略、注文実行、監視（モニタリング）といった各機能を独立して実装・拡張できます。本リポジトリはプロジェクトの基本構造とインターフェースの出発点を提供します。

バージョン: 0.1.0

---

## 目的（プロジェクト概要）

KabuSys は以下を目的とした軽量フレームワークです。

- 日本株の自動売買システムを構築するための枠組みを提供
- データ取得、戦略ロジック、注文発注、監視を役割別に分離
- 実装者が自分の戦略や取引インフラに合わせて拡張しやすい構造

現在のリポジトリは基本パッケージ構成のみを含むスケルトン実装です。実際のデータソースや証券会社APIとの接続、ストラテジーはユーザーが実装して利用します。

---

## 機能一覧

現状（スケルトン）に含まれる機能と、想定される主要機能は次のとおりです。

- パッケージ基本構造（モジュール）
  - data: 市場データの取得・前処理
  - strategy: 売買ロジック（シグナル生成）
  - execution: 注文の作成・送信・管理
  - monitoring: ログ、メトリクス、通知などの監視機能
- バージョン情報（kabusys.__version__ = "0.1.0"）
- 将来的に追加を想定する機能
  - 実際の証券会社API（例：kabutan、kabuステーション等）接続
  - 履歴データ取得とバックテスト機能
  - リアルタイム監視ダッシュボード（アラート）
  - 注文リスク管理（注文制限、最大注文サイズなど）

注: 現在はインターフェースのみで、具体的な実装（API呼び出しや戦略ロジック）は含まれていません。

---

## セットアップ手順

前提
- Python 3.8 以上を推奨（プロジェクトの要件に合わせて調整してください）

ローカル開発の基本手順:

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係のインストール
   - 現在 requirements.txt / setup.py が無い場合、依存はありません。将来的に必要なライブラリ（requests、pandas、numpy 等）があれば requirements.txt を追加して以下でインストールします。
   ```
   pip install -r requirements.txt
   ```
   - 開発中にソースを編集して動作させる場合（パッケージ化されている場合）:
   ```
   pip install -e .
   ```
   - パッケージ化されていないスケルトンのみの場合は、PYTHONPATH を設定して実行することもできます:
   ```
   PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
   ```

4. (任意) linter / formatter / テストのセットアップ
   - プロジェクトに合わせて flake8、black、pytest などを導入してください。

---

## 使い方（基本例）

このリポジトリはモジュールの雛形を提供します。以下は各モジュールに実装を追加して使う際の基本的なワークフロー例です。

1. バージョン確認
   ```python
   import kabusys
   print(kabusys.__version__)  # "0.1.0"
   ```

2. データモジュール（data）: データ取得クラスの例（実装はユーザーが行う）
   ```python
   # src/kabusys/data/my_data.py に実装する例
   class MarketDataSource:
       def fetch_price(self, symbol: str):
           # 実際のAPI呼び出しやDBアクセスを実装
           return {"symbol": symbol, "price": 1000}
   ```

3. 戦略モジュール（strategy）: シグナル生成クラスの例
   ```python
   # src/kabusys/strategy/my_strategy.py に実装する例
   class Strategy:
       def __init__(self, data_source):
           self.data_source = data_source

       def generate_signal(self, symbol: str):
           price = self.data_source.fetch_price(symbol)["price"]
           # 単純な例: 価格が閾値より安ければ買い
           if price < 900:
               return "BUY"
           return "HOLD"
   ```

4. 実行モジュール（execution）: 注文発注クラスの例
   ```python
   # src/kabusys/execution/my_executor.py に実装する例
   class Executor:
       def send_order(self, symbol: str, side: str, qty: int):
           # 証券APIへの発注処理を実装
           print(f"Order sent: {side} {qty} {symbol}")
   ```

5. 監視モジュール（monitoring）: ログ・通知クラスの例
   ```python
   # src/kabusys/monitoring/simple_monitor.py に実装する例
   class Monitor:
       def log(self, message: str):
           print(message)
   ```

6. 全体の簡単なフロー
   ```python
   from kabusys.data.my_data import MarketDataSource
   from kabusys.strategy.my_strategy import Strategy
   from kabusys.execution.my_executor import Executor
   from kabusys.monitoring.simple_monitor import Monitor

   data_source = MarketDataSource()
   strat = Strategy(data_source)
   exec = Executor()
   monitor = Monitor()

   symbol = "7203.T"  # 例: トヨタ自動車（証券コード）
   signal = strat.generate_signal(symbol)
   monitor.log(f"Signal for {symbol}: {signal}")

   if signal == "BUY":
       exec.send_order(symbol, "BUY", qty=100)
   ```

上記はあくまでサンプルです。実運用にはエラーハンドリング、接続リトライ、注文状態の確認、認証情報の安全管理、レート制限対策などが必要です。

---

## ディレクトリ構成

現在の主要ファイル・ディレクトリ構成は次の通りです。

- src/
  - kabusys/
    - __init__.py           # パッケージ初期化、__version__ 定義
    - data/
      - __init__.py         # データ取得関連モジュールを配置
    - strategy/
      - __init__.py         # 戦略ロジックを配置
    - execution/
      - __init__.py         # 注文実行関連を配置
    - monitoring/
      - __init__.py         # 監視・ログ関連を配置

例（ファイルツリー）
```
.
└─ src
   └─ kabusys
      ├─ __init__.py
      ├─ data
      │  └─ __init__.py
      ├─ strategy
      │  └─ __init__.py
      ├─ execution
      │  └─ __init__.py
      └─ monitoring
         └─ __init__.py
```

---

## 開発・拡張方法のガイド

- 各サブパッケージ（data, strategy, execution, monitoring）に具体的なクラス・関数を実装してください。
- インターフェースを統一しておくと、異なる実装（モック／実装）を差し替えやすくなります（例: StrategyBase、ExecutorBase の抽象基底クラスを定義）。
- 機密情報（APIキー等）は環境変数やシークレット管理ツールで管理し、ソース管理に含めないでください。
- ローカルでのデバッグ・テストのために、モックデータソースやサンドボックス環境を用意してください。

---

## ライセンス / コントリビューション

- ライセンス情報がプロジェクトに含まれていない場合は、利用前に作者に確認してください。
- コントリビューションされる場合は、Issue や Pull Request にて目的・変更点を明記してください。

---

必要であれば、README にサンプル戦略の完全な実装、テストのテンプレート（pytest）、CI 設定（GitHub Actions）などを追加することもできます。追加したい内容や実装方針があれば教えてください。
# KabuSys

KabuSys は日本株向けの自動売買（アルゴリズムトレーディング）システムの骨格となる Python パッケージです。現在はパッケージ構成（モジュールの雛形）を提供しており、実際のデータ取得・戦略・注文実行・監視処理を各サブパッケージに実装して拡張することを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的: 日本株の自動売買システムの基本構造を提供し、各機能（データ取得、売買戦略、注文実行、監視）を分離して実装できるようにする。
- 現状: パッケージの骨格（`kabusys` パッケージと 4 つのサブパッケージ `data`, `strategy`, `execution`, `monitoring`）のみが用意されています。各サブパッケージの中に具体的な実装を追加して利用します。

---

## 機能一覧（想定）

現時点ではインターフェース/構造のみですが、今後以下の機能を実装することを想定しています。

- data: 市場データの取得・前処理（板情報、約定履歴、日足・分足など）
- strategy: 売買戦略（シグナル生成、ポジション管理、リスク管理）
- execution: 注文の送信・キャンセル・約定確認（証券会社APIとの連携）
- monitoring: 稼働状況の監視・ログ収集・アラート通知

---

## セットアップ手順

推奨環境
- Python 3.8 以上

セットアップ手順（開発向け、ソースからインストールする例）:

1. リポジトリをクローンする
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化する（例: venv）
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

3. 開発用に依存関係をインストールする
   - 現在 requirements は定義されていません。必要なライブラリがある場合は `requirements.txt` や `pyproject.toml` に追加してください。
   - 開発中は編集を反映させるために editable インストールを行うと便利です:
     ```
     pip install -e .
     ```
     （`setup.py` または `pyproject.toml` が必要です。なければ直接ソースを参照して実行してください。）

---

## 使い方

現状はパッケージの雛形のみのため、基本的なインポート例と拡張方法を示します。

- バージョン確認、パッケージのインポート例
  ```python
  import kabusys

  print(kabusys.__version__)  # -> "0.1.0"

  # サブパッケージを参照
  import kabusys.data
  import kabusys.strategy
  import kabusys.execution
  import kabusys.monitoring
  ```

- サブパッケージにクラス・関数を追加する例
  1. `src/kabusys/data/market.py` を作成してデータ取得クラスを実装する
  2. `src/kabusys/strategy/my_strategy.py` に戦略のロジックを実装する
  3. `src/kabusys/execution/executor.py` に注文実行インターフェースを実装する
  4. `src/kabusys/monitoring/health.py` に監視/ログ収集機能を実装する

- 例: シンプルな戦略の呼び出し（擬似コード）
  ```python
  from kabusys.data.market import MarketDataClient
  from kabusys.strategy.my_strategy import MyStrategy
  from kabusys.execution.executor import Executor

  data_client = MarketDataClient(...)
  strategy = MyStrategy(...)
  executor = Executor(...)

  # データ取得 -> シグナル生成 -> 注文実行
  df = data_client.get_recent_prices('7203')  # 銘柄コードの例
  signal = strategy.generate_signal(df)
  if signal.should_buy:
      executor.buy('7203', quantity=100)
  elif signal.should_sell:
      executor.sell('7203', quantity=100)
  ```

---

## ディレクトリ構成

現在のプロジェクト構成（主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py                # パッケージ定義（バージョン、エクスポート）
    - data/
      - __init__.py              # データ関連モジュール用パッケージ
    - strategy/
      - __init__.py              # 戦略関連モジュール用パッケージ
    - execution/
      - __init__.py              # 注文実行関連モジュール用パッケージ
    - monitoring/
      - __init__.py              # 監視関連モジュール用パッケージ

ファイルの中身（抜粋）
- src/kabusys/__init__.py
  - ドキュメンテーション文字列: "KabuSys - 日本株自動売買システム"
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 開発・拡張のヒント

- 各サブパッケージは責務を明確に分ける（データ取得、戦略、実行、監視）。
- 外部 API（証券会社やマーケットデータ提供元）と接続する場合は、接続情報や API キーを環境変数で管理することを推奨します。
- 注文実行はバックテストと実運用で実装を分ける（実運用時は十分なエラーハンドリングと冪等性を確保）。
- ロギング、例外処理、ユニットテストを早めに整備すると保守しやすくなります。

---

README は必要に応じて、依存関係（requirements）、ライセンス、貢献ガイド、CI 設定などを追記してください。必要があればテンプレートの追加や具体的な実装サンプル（データ取得クラス、戦略アルゴリズム、注文実行ラッパー）を作成します。
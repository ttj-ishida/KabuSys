# KabuSys

KabuSys は日本株向けの自動売買システム土台（ライブラリ）です。データ取得・スキーマ管理、環境設定、戦略／発注／モニタリング領域の基盤コードを提供します。本リポジトリはシステムのコア部分（設定管理、DuckDB スキーマ定義、接続ユーティリティ等）を含みます。

バージョン: 0.1.0

---

## 主な特徴
- 環境変数／.env ファイルの自動読み込み（プロジェクトルートを自動検出）
- 設定ラッパー（settings）で環境変数を型付きで取得
- DuckDB を用いた多層（Raw / Processed / Feature / Execution）データスキーマ定義と初期化
- インメモリ DB 対応（":memory:"）
- 発注・約定・ポートフォリオなどの実行レイヤー用テーブル群と索引を用意
- 将来的な戦略・実行・モニタリングモジュール用のパッケージ構造を用意

---

## 機能一覧
- .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）
  - プロジェクトルート判定は .git または pyproject.toml を起点に行う
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- Settings クラス経由で以下の設定を取得
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（省略可、デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH（データベースパス）
  - KABUSYS_ENV（development | paper_trading | live）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DuckDB スキーマ管理
  - raw_prices / raw_financials / raw_news / raw_executions などの Raw レイヤー
  - prices_daily / market_calendar / fundamentals / news_articles などの Processed レイヤー
  - features / ai_scores の Feature レイヤー
  - signals / signal_queue / orders / trades / positions / portfolio_performance の Execution レイヤー
  - よく使うクエリ向けの索引を自動作成
  - init_schema() で冪等にテーブルを作成

---

## 必要条件
- Python 3.9+
- duckdb（Python パッケージ）
- （任意）pip 等のパッケージ管理ツール

---

## セットアップ手順

1. リポジトリをクローン、あるいはパッケージを配置
2. 仮想環境を作成／有効化（推奨）
3. 必要パッケージをインストール
   - 例:
     ```
     pip install duckdb
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```
4. プロジェクトルートに `.env`（と任意で `.env.local`）を作成して必要な環境変数を設定
   - 自動検出は .git または pyproject.toml を起点に行います

---

## 環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env のパース仕様（主要点）
- 空行や '#' で始まる行は無視
- export KEY=val 形式に対応
- 値がクォートされている場合はバックスラッシュエスケープに対応
- クォートなしのコメントは '#' の直前がスペース/タブの場合のみコメントと認識

---

## 使い方（基本例）

- 設定を利用する:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print("KabuSys 環境:", settings.env)
  ```

- DuckDB スキーマを初期化する:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # ファイル DB を初期化（親ディレクトリが無ければ自動作成されます）
  conn = init_schema(settings.duckdb_path)

  # インメモリ DB を使う場合
  mem_conn = init_schema(":memory:")
  ```

- 既存 DB に接続する:
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  ```

- 自動 .env 読み込みを無効化（テストなど）:
  - 環境変数に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して Python を起動します。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
    - パッケージのバージョンやエクスポート（data, strategy, execution, monitoring）
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - schema.py
      - DuckDB の DDL 定義、init_schema(), get_connection()
  - strategy/
    - __init__.py（戦略関連モジュール用プレースホルダ）
  - execution/
    - __init__.py（発注・実行関連モジュール用プレースホルダ）
  - monitoring/
    - __init__.py（モニタリング関連モジュール用プレースホルダ

---

## 開発メモ / 注意点
- init_schema() は冪等（既存テーブルがあればスキップ）なので安全に何度でも呼べます。
- settings の一部プロパティは未設定時に ValueError を投げます（必須設定の検証）。
- DuckDB ファイルパスの親ディレクトリがなければ自動で作成されます。
- 外部 API（J-Quants、kabuステーション、Slack）用のトークン等は .env に安全に保管してください。
- 現在はフレームワークの基盤部分が揃っている段階であり、戦略・実行の詳細実装は各モジュールに追加していく想定です。

---

必要であれば README に使用例（SQL クエリ例、テーブル一覧のサンプルクエリ）、.env.example のテンプレート、テスト実行手順などを追加します。どの情報をさらに載せたいか教えてください。
CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティック・バージョニングを使用します。

[全般]
- 初期リリースとしてコードベースから推測される機能・挙動を記載しています。
- リリース日はソースコード解析時点の日付を使用しています。

Unreleased
----------
- なし

0.1.0 - 2026-03-15
------------------

Added
- パッケージの初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パブリック API（__all__）: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは実行環境から設定を読み込む自動ロード機能を実装
    - プロジェクトルートの検出は、__file__ を起点に親ディレクトリから .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数は保護（protected）され、.env の上書きを防止する仕組みを導入。
  - .env ファイルのパーサー（_parse_env_line）を実装
    - export KEY=val 形式に対応
    - シングル／ダブルクォートされた値のエスケープ（バックスラッシュ）を正しく解釈
    - クォート無し値の行末コメント（#）の扱いは、直前がスペースまたはタブの場合のみコメントと判断
    - 空行や先頭が # の行を無視
  - .env 読み込み時の安全処理
    - ファイルオープンに失敗した場合は警告を出して処理を継続
    - override パラメータにより既存環境変数の上書き可否を制御
  - 必須環境変数チェック(_require) と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN（J-Quants）
    - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API、デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - システム運用モード: KABUSYS_ENV（development / paper_trading / live）を検証
    - ログレベル: LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL）を検証
    - env 判定ヘルパー: is_live, is_paper, is_dev

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - データレイヤを想定した多層スキーマを定義（Raw / Processed / Feature / Execution）
  - テーブル定義（主なテーブル）
    - Raw Layer:
      - raw_prices (date, code, open/high/low/close, volume, turnover, fetched_at)
      - raw_financials (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at)
      - raw_news (id, datetime, source, title, content, url, fetched_at)
      - raw_executions (execution_id, order_id, datetime, code, side, price, size, fetched_at)
    - Processed Layer:
      - prices_daily (日足)
      - market_calendar (取引日情報: is_trading_day, is_half_day, is_sq_day, holiday_name)
      - fundamentals (整形済み決算データ)
      - news_articles, news_symbols (ニュースと関連銘柄)
    - Feature Layer:
      - features (momentum, volatility, per/pbr/div_yield, ma200_dev 等)
      - ai_scores (sentiment, regime, ai_score 等)
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック
    - PRIMARY KEY、FOREIGN KEY（ON DELETE 挙動指定）、CHECK 制約（価格 >= 0、サイズ > 0、列値の列挙チェック等）を網羅
  - インデックス定義（頻出クエリパターンを想定）
    - prices_daily(code, date)、features(code, date)、ai_scores(code, date)
    - signal_queue(status)、orders(status)、orders(signal_id)、trades(order_id)、news_symbols(code) 等
  - スキーマ初期化 API
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの親ディレクトリが存在しない場合は自動作成
      - :memory: を指定してインメモリ DB を使用可能
      - DDL を順序付けて実行しテーブル・インデックスを作成（冪等）
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への単純接続（初回は init_schema を推奨）

- モジュールの基本構成ファイルを追加
  - src/kabusys/__init__.py（パッケージ説明とバージョン）
  - 空のパッケージ初期ファイル: src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/monitoring/__init__.py

Changed
- 初回リリースのため変更履歴なし

Fixed
- 初回リリースのため修正履歴なし

Security
- 環境変数の自動読み込み時、OS 環境（既にセットされたキー）を保護する仕組みを導入し、意図せぬ上書きを防止
- .env の読み込みはプロジェクトルート検出に失敗した場合はスキップされる（安全側の動作）

Notes / Migration
- DuckDB の利用にあたっては、初回起動時に init_schema() を呼び出してスキーマを作成することを推奨します。get_connection() は既存スキーマがあることを前提としています。
- 必須環境変数が未設定の場合、Settings の各プロパティは ValueError を投げます。.env.example を参照して .env を用意してください（リポジトリに .env.example がある想定）。
- .env のパース動作はシェルの慣例にかなり近い挙動を再現していますが、極端なケース（複雑なネストや非標準の書式）では期待通りに解釈されない可能性があります。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで、自動で .env を読み込まないテスト用の実行などが可能です。

Breaking Changes
- なし（初回リリース）

--- 

作成した CHANGELOG はソースコードから推測して記載しています。必要であれば各項目をより具体的なリリースノートやチケット番号に置き換えます。
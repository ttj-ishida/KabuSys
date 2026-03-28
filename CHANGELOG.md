# Changelog

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

- リリース日付は変更履歴作成時点のコードベースから推測しています。
- 各項目では実装上の主要機能、設計上の注意点、外部依存や環境変数を明記しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-28
最初の公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主に以下のサブパッケージ・機能を実装しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として定義。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
  - .env パーサ (_parse_env_line) はコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントを正しく扱う。
  - .env 読み込みの保護機構（protected set）を実装し OS 環境変数の上書きを防止。
  - Settings クラスを提供し、各種必須／任意設定値をプロパティとして取得可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - ヘルパー: is_live / is_paper / is_dev

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄単位のニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価を行い ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で実装。
  - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
  - JSON mode を利用した厳密なレスポンス期待、レスポンスのバリデーションとスコアの ±1.0 クリップ実装。
  - 失敗耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、その他エラーはスキップして処理継続。
  - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。
  - テスト容易性のため OpenAI 呼び出しは内部関数 _call_openai_api を経由しパッチ可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を組み合わせ、日次で市場レジーム（bull/neutral/bear）を決定する score_regime 関数を実装。
  - ma200_ratio 計算（ルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用）、マクロ記事の抽出、OpenAI でのスコア化、スコア合成、market_regime への冪等書き込みを実装。
  - API エラー時は macro_sentiment=0.0 のフェイルセーフを持つ。OpenAI 呼び出しのリトライとログ対応あり。
  - テスト用に _call_openai_api を差し替え可能。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。データ不足は None を返す。
    - calc_volatility(conn, target_date): ATR20、ATR比、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER/ROE を計算。
    - 実装は DuckDB の SQL を活用し、外部 API へアクセスしない。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト: 1,5,21 営業日）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。データ不足時は None。
    - rank(values): 同順位は平均ランクで扱う安定したランク関数。
    - factor_summary(records, columns): count/mean/std/min/max/median の基本統計量を算出。
  - kabusys.research.__init__ で一部ユーティリティ（zscore_normalize など）を再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が存在しない場合は曜日ベース（週末除く）でフォールバックする堅牢な設計。
    - calendar_update_job(conn, lookahead_days) により J-Quants API から差分取得し market_calendar を冪等的に更新（バックフィル・健全性チェック付き）。
  - pipeline / etl:
    - ETLResult データクラスを提供（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETL の支援ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - ETL 設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast ではない）を備える。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。

- その他
  - 各所で DuckDB を用いた SQL 実装を採用し、外部ライブラリ（pandas 等）への依存を排除。
  - コード全体で「datetime.today()/date.today() を直接参照しない」設計を採用し、ルックアヘッドバイアス対策を徹底。
  - ロギングと警告の整備（データ不足、API エラー、ROLLBACK 失敗等に関するログ出力）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 初期リリースのため該当なし。

---

## マイグレーション / 利用時の注意
- OpenAI API を利用する機能（score_news, score_regime）は OPENAI_API_KEY の設定が必須。api_key 引数でも注入可能。
- .env 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。パッケージ配布後に自動ロードを望まない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- DuckDB の executemany は空リスト受け入れに制約があるバージョン（例: 0.10）を考慮した実装になっています。古い DuckDB を使う場合は注意してください。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を使用。レスポンスのパースに失敗した場合はフォールバック（0.0 / スキップ）する設計です。

もしこの CHANGELOG に補足してほしい点（例: 日付の変更、より詳細な項目分解、リリースノートの英語版など）があれば教えてください。
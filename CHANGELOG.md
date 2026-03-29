Keep a Changelog
=================

すべての重要な変更はこのファイルに記録されます。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初期リリース。パッケージ名: `kabusys`（version 0.1.0）。
- パッケージ公開インターフェースを追加:
  - `kabusys.__all__` により "data", "strategy", "execution", "monitoring" を公開。
- 設定 / 環境変数管理:
  - `kabusys.config.Settings` と `settings` インスタンスを追加。以下の主要な設定プロパティを提供:
    - J-Quants / kabuAPI / Slack トークン関連 (`jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`, `slack_bot_token`, `slack_channel_id`)。
    - DB パス (`duckdb_path`, `sqlite_path`) の既定値（`data/kabusys.duckdb`, `data/monitoring.db`）。
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証ロジック。
    - `is_live`, `is_paper`, `is_dev` のユーティリティプロパティ。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込み。
    - OS 環境変数を一時保護して `.env.local` による上書きを制御。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パーサは `export KEY=val` 形式、クォート、エスケープ、インラインコメント対応。
- AI（自然言語処理）モジュール:
  - `kabusys.ai.news_nlp`:
    - ニュース記事の銘柄別センチメント解析を行い、`ai_scores` テーブルへ書き込むメイン関数 `score_news(conn, target_date, api_key=None)` を提供。
    - タイムウィンドウ計算 (`calc_news_window`)：JST 基準で前日 15:00 ～ 当日 08:30 を対象（内部は UTC naive datetime）。
    - バッチ（最大 20 銘柄）で OpenAI（`gpt-4o-mini`）へ送信。1 銘柄あたりの記事上限・文字数上限のトリム処理を実装。
    - レスポンス検証機構（JSON 抽出・構造チェック・スコア数値化・±1.0 クリップ）。
    - リトライ・バックオフ実装（429・ネットワーク断・タイムアウト・5xx を対象）。
    - API 呼び出し関数 `_call_openai_api` はテスト時にモック差替え可能。
  - `kabusys.ai.regime_detector`:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ系ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（`bull` / `neutral` / `bear`）を日次で算出する `score_regime(conn, target_date, api_key=None)` を提供。
    - マクロニュース抽出（マクロキーワードリスト）・LLM 呼び出し（`gpt-4o-mini`）・リトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - 計算結果はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等的に `market_regime` テーブルへ保存。
- Data モジュール:
  - `kabusys.data.calendar_management`:
    - JPX カレンダーの管理、営業日判定、翌営業日/前営業日/期間内営業日取得、SQ 日判定などのユーティリティを追加（`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`）。
    - DB データがない場合は曜日ベース（平日）でフォールバックする設計。
    - カレンダー更新バッチ `calendar_update_job(conn, lookahead_days=90)` を提供。J-Quants クライアント経由で差分取得 → 冪等保存。バックフィルと健全性チェックあり。
  - `kabusys.data.pipeline`:
    - ETL 処理向けのユーティリティと `ETLResult` データクラスを実装（差分取得、保存、品質チェックの結果集約、エラー/品質問題の収集）。
    - `_get_max_date` などの内部ユーティリティを含む。
  - `kabusys.data.etl`:
    - `ETLResult` を再エクスポート。
- Research モジュール:
  - `kabusys.research.factor_research`:
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を提供:
      - `calc_momentum(conn, target_date)`：mom_1m/3m/6m、ma200_dev 等（データ不足時は None）。
      - `calc_volatility(conn, target_date)`：20 日 ATR、相対 ATR、平均売買代金、出来高比率等。
      - `calc_value(conn, target_date)`：PER（EPS が 0/欠損時は None）、ROE（raw_financials からの最新値）。
    - DuckDB の SQL ウィンドウ関数を多用し、prices_daily / raw_financials のみ参照。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21] 日）。
    - IC（Spearman の ρ）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)`。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク）。
    - 統計サマリー `factor_summary(records, columns)`（count/mean/std/min/max/median）。
    - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリのみで実装。
- テスト・デバッグ配慮:
  - OpenAI API 呼び出しの内部関数をテストからモック可能な形で分離（`_call_openai_api`）。
  - DuckDB の executemany の挙動（空リスト不可）への対処を実装。

Security
- .env 自動ロードは OS 環境変数を上書きしないよう保護（`.env.local` は上書き可だが保護された OS 環境キーは除外）。
- API キー未設定時は明確な `ValueError` を発生させることで安全に失敗させる設計。
- OpenAI 呼び出しでの失敗は例外を投げずにフェイルセーフ（中立スコア）で継続する箇所があり、直接的に注文などに結びつかないよう配慮。

Notes / Design decisions
- ルックアヘッドバイアス対策: 全ての分析/スコアリング関数は内部で `datetime.today()` や `date.today()` を参照せず、外部から `target_date` を注入する設計。
- DB 書き込みは基本的に冪等性を担保（DELETE→INSERT や ON CONFLICT 相当）し、トランザクションでまとめている。
- 外部依存は最小限（DuckDB, OpenAI SDK）。研究用機能は pandas 等を使わず標準ライブラリで実装。
- OpenAI モデルはデフォルトで `gpt-4o-mini` を指定。レスポンスは JSON Mode を期待し、パース失敗時の復元処理を実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）
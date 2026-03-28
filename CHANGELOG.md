# CHANGELOG

すべての変更は Keep a Changelog の形式およびセマンティックバージョニングに従います。  

次の変更履歴は、ソースコードから機能・仕様・設計方針を推測して作成しています。

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリース: kabusys パッケージ (日本株自動売買システム) を公開。
  - パッケージメタ:
    - バージョン: 0.1.0
    - エントリ: src/kabusys/__init__.py

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。CWD に依存しない実装。
    - 読み込み順: OS 環境変数 > .env.local（override=True）> .env（override=False）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサは `export KEY=val` 形式、シングル／ダブルクォート（エスケープ処理）とコメントの扱いに対応。
    - 既存 OS 環境変数を保護する protected キーの概念を導入。
  - Settings クラスを提供（settings インスタンスで使用）。
    - J-Quants / kabu / Slack / データベースパス等の取得プロパティ（必須項目は未設定時に ValueError を送出）。
    - デフォルト値（例: KABUSYS_ENV=development、LOG_LEVEL=INFO、DUCKDB_PATH/SQLITE_PATH の既定パス）。
    - env/log_level 値の検証（有効な列挙値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコア（kabusys.ai.news_nlp）
    - score_news 関数で raw_news + news_symbols を読み、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1 銘柄あたりの記事は最新 N 件・文字数上限でトリムしてプロンプト生成（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理: 最大 _BATCH_SIZE 件の銘柄を 1 API 呼び出しで処理。
    - レート制限 (429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ実装。
    - レスポンスの厳密なバリデーションを実装（JSON 抽出、"results" 配列、code/score 検証、±1.0 にクリップ）。
    - DuckDB への書き込みは部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT（冪等保存）。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で抽象化しモック差替え可能。
    - DuckDB 0.10 の executemany に関する空リスト制約を考慮した実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロ記事抽出はマクロキーワードリストに基づくフィルタリング（件数上限）。
    - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - 合成スコアを閾値で判定し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しでのリトライ / エラーハンドリングを実装。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離(ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS=0/欠損時は None）。
    - 全関数とも DuckDB 接続を受け取り SQL ベースで計算、返却は (date, code) をキーとする dict のリスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得（LEAD を利用）。
    - calc_ic: スピアマン（ランク）相関で Information Coefficient を算出。レコード不足/ゼロ分散時は None。
    - rank: 同順位は平均ランクにするランク化実装（丸めで ties の検出漏れを防止）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは data.stats の zscore_normalize 等を再公開。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ユーティリティを実装。
    - market_calendar が存在しない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から JPX カレンダーを差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装（直近・将来日付の検査）。
    - 最大探索日数やバックフィル日数等の安全パラメータを導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー一覧などを格納）。
    - _get_max_date 等の DB ヘルパーを実装。
    - ETL の設計方針: 差分更新、バックフィル、品質チェックの実行（quality モジュールと連携）。品質問題は収集して呼び出し元に委ねる設計（Fail-Fast ではない）。
    - data.etl モジュールは ETLResult を再エクスポート。

Misc / Implementation notes
- DuckDB を主要なローカル DB として利用（クエリは DuckDB SQL）。
- OpenAI SDK（OpenAI クライアント）を前提とした実装（gpt-4o-mini を想定）。
- ルックアヘッドバイアス対策: 日時系関数（score_news, score_regime 等）は内部で date.today() を直接参照しない（target_date パラメータで制御）。
- テストしやすさ: OpenAI 呼び出し箇所を差し替え可能にしてユニットテストを容易化。
- ロギング・警告を多用し失敗時に安全なフォールバック（例: マクロセンチメント 0.0）を採用。
- 環境変数未設定時は ValueError を投げる設計で、.env.example に従ったセットアップを想定。

Known limitations / Notes
- 一部関数は外部クライアント（jquants_client）や quality モジュール等に依存しており、これらの実装/設定が必要。
- OpenAI API 利用には OPENAI_API_KEY が必須（引数経由で注入可能）。
- DuckDB executemany の実装差異に配慮したコードが含まれる（空リストバインド回避）。
- 現時点で PBR や配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。

(注) 本 CHANGELOG はソースコードからの推測に基づくため、リリースノートとして公式に使用する場合は実際のコミット履歴やリリース管理情報での精査を推奨します。
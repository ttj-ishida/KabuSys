# Changelog

すべての変更は Keep a Changelog の形式に従います。  
重大/後方互換性に関する情報は各項目に記載しています。

現在のリリース履歴
- Unreleased
- [0.1.0] - 2026-03-31

## [Unreleased]
（未リリースの変更はありません）

## [0.1.0] - 2026-03-31

Added
- パッケージ初期公開（kabusys v0.1.0）
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョン "0.1.0" を公開。パッケージの公開 API として data, strategy, execution, monitoring を __all__ でエクスポート。
- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - .env ファイル（プロジェクトルート判定は .git または pyproject.toml）を自動で読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート付き値（バックスラッシュによるエスケープ処理を考慮）
    - クォートなし値でのインラインコメント（# の前が空白/タブの場合にコメントと判定）
    - 無効行や空行・コメント行をスキップ
  - 環境変数必須取得用ヘルパー _require と Settings クラスを提供（主な設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）
  - 設定値検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許容
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容
- AI モジュール（src/kabusys/ai/）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に換算して DB クエリ）
    - バッチ仕様: 最大 20 銘柄/回、1 銘柄あたり最大 10 記事、最大 3000 文字にトリム
    - 再試行・フォールバック: 429/接続断/タイムアウト/5xx を指数バックオフでリトライ。失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスを厳密にバリデーション（JSON 抽出、results 配列、code と score の型検証、未知コード無視、数値チェック、±1.0 にクリップ）。
    - score_news API: DuckDB 接続と target_date を受け取り、書き込み件数を返す。api_key 引数または環境変数 OPENAI_API_KEY を使用して OpenAI を呼び出す。
    - JSON パースで前後余剰テキストが混じる場合の復元ロジックを実装。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む処理を実装。
    - マクロ記事はニュースタイトルからキーワード（例: 日銀、金利、Fed 等）で抽出。最大 20 件まで。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を扱う。
    - OpenAI 呼び出し（gpt-4o-mini、JSON Mode）に対してリトライ/バックオフを実装。API フェイル時は macro_sentiment=0.0 にフォールバックして処理を継続。
    - レジームスコア合成式とラベル付け、そして BEGIN/DELETE/INSERT/COMMIT による冪等性保護を実装。
    - score_regime API: DuckDB 接続と target_date、api_key（または環境変数 OPENAI_API_KEY）を受け取り整数 1 を返す（成功時）。
  - 共通設計方針:
    - datetime.today()/date.today() を参照せず、target_date ベースで処理（ルックアヘッドバイアス防止）。
    - テスト容易性のため _call_openai_api を patch 可能にしている（unit test 用の差し替え想定）。
- Research モジュール（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）および Liquidity 指標の計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials を参照して SQL ベースで計算。データ不足時は None を返す設計。
    - 結果は (date, code) をキーにした dict のリストで返却。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient, calc_ic）、ランキング（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応、horizons の検証あり（1〜252）。
    - calc_ic はスピアマンランク相関を自前で計算（外部依存なし）。
  - research パッケージ __all__ で主要関数を公開。
- Data モジュール（src/kabusys/data/）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理: market_calendar テーブルの利用、DB 値優先の営業日判定と曜日ベースのフォールバック、next/prev/get_trading_days/is_sq_day 等のユーティリティを実装。
    - calendar_update_job: J-Quants API 経由で差分取得 → market_calendar に冪等保存（fetch/save は jquants_client を利用）。バックフィル、健全性チェック、ログ出力を実装。
  - pipeline / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL パイプライン用 ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー一覧などを保持、to_dict を提供）。
    - 差分更新のためのユーティリティ（最終日取得など）を実装。バックフィル日数や最小データ日付などの定数を定義。
    - データ保存は idempotent（ON CONFLICT DO UPDATE 想定）に設計。
  - jquants_client を想定したデータ取得フローのためのフックを用意（fetch/save を呼び出す実装）。
- その他
  - モジュール内で DuckDB を前提とした SQL 実装を多用（DuckDBPyConnection 型注釈）。
  - ロギングと堅牢なエラーハンドリング（ROLLBACK 時の二重例外対策、警告/情報ログの充実）を重視した設計。

Changed
- 初版のため既知の挙動や設計方針をドキュメント化（各モジュール冒頭の docstring に詳細な処理フロー、設計方針、フォールバックロジックを追加）。

Fixed
- 初版（該当なし）

Deprecated
- 初版（該当なし）

Removed
- 初版（該当なし）

Security
- OpenAI API キーの取り扱い:
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY を用いる仕様。キーの管理は利用者側で行うこと。
  - 自動 .env ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（テストや CI の秘匿対策に利用可）。

注意事項（移行・利用ガイド）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須となる。AI 機能を使う場合は OPENAI_API_KEY が必要。
- デフォルトパス:
  - DUCKDB_PATH のデフォルトは data/kabusys.duckdb
  - SQLITE_PATH のデフォルトは data/monitoring.db
- DuckDB の互換性:
  - 一部実装は DuckDB の executemany の挙動（空リスト不可）やリスト型バインドの挙動に合わせた回避実装を含む（executemany を使った個別 DELETE など）。
- ルックアヘッドバイアス対策:
  - 全ての AI/リサーチ処理で datetime.today()/date.today() を内部参照せず、外部から与えられる target_date を用いる設計となっているため、運用時は target_date の取り扱いに留意してください。

お問い合わせ・貢献
- 問題報告や機能提案はリポジトリの Issue を使用してください。テスト容易性のために _call_openai_api の patch などモック用フックを用意しています。
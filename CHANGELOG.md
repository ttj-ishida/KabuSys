CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
このプロジェクトはセマンティックバージョニングに従います。

リンク: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （次リリース用のプレースホルダ）

0.1.0 - 2026-03-31
------------------

Added
- 初回公開。日本株自動売買プラットフォームの基礎モジュール群を追加。
  - パッケージのルート: kabusys (version 0.1.0)
    - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパースは以下に対応:
    - 空行・コメント（#）の無視、先頭に "export " がある形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなしの場合はインラインコメント判定のルール（'#' の直前が空白/タブならコメント扱い）。
  - _load_env_file による上書き制御（override）と OS 環境変数保護（protected set）。
  - Settings クラスを提供し、アプリケーションで使用する環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス設定）
    - 監視用閾値（CPU/MEM/DISK）や PID_FILE_PATH
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティ

- AI (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを結合し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC換算で扱う）。calc_news_window 関数を提供。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄（_BATCH_SIZE）を処理。1 銘柄あたりの記事上限/文字上限を設定（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - エラーハンドリング・リトライ: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンス検証: JSON の復元ロジック、"results" リスト存在チェック、code と score の型検証、スコアを ±1.0 にクリップ。
    - DB 書き込みは部分失敗に強い実装（取得した code のみ削除 → INSERT）し、DuckDB の executemany 空リスト制約に対応。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api を通しており unittest.mock.patch による差し替えを想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードリストと最大記事数を定義し、raw_news からタイトルを抽出して LLM 評価を実施。
    - OpenAI 呼び出しに対する堅牢なリトライロジックとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジーム合成結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - lookahead バイアス防止設計: date 引数ベースで動作し、datetime.today()/date.today() を参照しない。prices_daily クエリは target_date 未満を使用。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録がないまたは値が NULL の場合は曜日ベースのフォールバック（土日非営業日）。
    - next/prev_trading_day は最大探索日数制限を設けて無限ループを防止。
    - calendar_update_job: J-Quants クライアント経由で差分取得し market_calendar を更新。バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - jquants_client（外部）を利用した fetch/save の呼び出し箇所を用意（実装は依存モジュール側）。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得、保存（idempotent）、品質チェックの流れを想定したインタフェースを実装。
    - ETLResult は品質問題（quality.QualityIssue のリスト）やエラー概略を収集でき、辞書化メソッドを提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比を計算。データ不足処理あり。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出。直近の財務データを target_date 以前から取得。
    - すべて DuckDB 上の SQL を用いて実行し、(date, code) ベースの辞書リストを返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得。入力検証（horizons の範囲）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクを返す実装（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。None を除外。
    - pandas 等外部依存を使わない純標準ライブラリ実装。

Other notable design decisions / safety
- lookahead バイアス防止: AI モジュール・リサーチ系は date 引数ベースで動作し、実行時の現在時刻参照を避ける設計。
- DuckDB を主要なローカル分析 DB として利用（SQL を多用）。
- 外部 API 呼び出し（OpenAI / J-Quants 等）はリトライ戦略とフェイルセーフ（継続/スキップ）を採用し、例外の一部は上位に伝播するが多くはログ出力してスキップする実装方針。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を通すことでモック差し替えが可能。
- ロギングを活用し、異常時は warning/info/exception を出力。

Breaking Changes
- 初版のため無し。

Deprecated
- 初版のため無し。

Removed
- 初版のため無し。

Security
- 初版のため該当なし。

注記（Migration / Usage）
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能を使う場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants を利用する ETL）
  - KABU_API_PASSWORD（kabuステーション API 利用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知機能）
- .env 自動読み込みはプロジェクトルート検出に依存。パッケージ配布後や CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自前で環境設定を注入してください。
- DuckDB / SQLite のデフォルトパスは Settings で設定可能（DUCKDB_PATH/SQLITE_PATH）。

開発や運用での補足情報はソース内の docstring とログメッセージを参照してください。
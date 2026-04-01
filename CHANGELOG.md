Keep a Changelog
================

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット
- リリースは安定版、プレリリース、または未リリース（Unreleased）として順に記載します。
- 各リリース下に Added / Changed / Fixed / Deprecated / Removed / Security のセクションを置きます。

Unreleased
---------

（現在なし）

0.1.0 - 2026-04-01
------------------

初回リリース。以下の機能群を実装・公開しました。

Added
- パッケージの公開
  - kabusys パッケージを初回公開。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を追加。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local から自動で環境変数を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等に便利）。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォートされた値のバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント判定（直前がスペース/タブの場合のみ）
  - 読み込み時は OS 環境変数を保護するため protected set を利用して .env.local の上書きを制御。
  - Settings クラスを提供し、プロパティ経由で設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト local）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（data/...）
    - 監視用設定: PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - システム環境: KABUSYS_ENV の検証（development, paper_trading, live のみ許容）、LOG_LEVEL の検証
    - ユーティリティ: is_live / is_paper / is_dev

- AI 関連（kabusys.ai）
  - ニュース NLU/スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して DB クエリに利用。
    - バッチ処理: 1 API コールで最大 20 銘柄（_BATCH_SIZE=20）。
    - 1 銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフによるリトライ実装（_MAX_RETRIES）。
    - JSON Mode のレスポンス検証と厳格なバリデーション（results 配列、code/score の存在・型検査）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（該当 code を DELETE -> INSERT）。
    - DuckDB の executemany の挙動（空リスト不可）への対処を実装。
    - テスト容易性: API 呼び出し部分は _call_openai_api を patch して差し替え可能。
    - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロニュースは raw_news のマクロキーワードでフィルタ（キーワードリストを定義）。
    - LLM 呼び出しは gpt-4o-mini（JSON 出力）を使用。API エラー・パース失敗時は macro_sentiment=0.0 としてフェイルセーフ。
    - レジームスコアは clip し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK を試行して例外を伝搬。
    - API キー注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
    - 設計上、datetime.today()/date.today() を用いないことでルックアヘッドバイアスを防止。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（単純平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から直近財務を取得し PER（EPS が 0/NULL の場合 None）、ROE を計算。
    - DuckDB ベースの SQL 実装（外部 API にはアクセスしない）。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定日から各ホライズン後のリターンを一括で計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマン ランク相関（IC）を計算。十分なサンプル数（>=3）でなければ None。
    - rank: 同順位は平均ランクを返す安定実装（丸め対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュールを追加:
    - market_calendar を基に営業日判定・前後の営業日取得・期間内営業日列挙・SQ 日判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job: J-Quants からの差分取得と market_calendar への冪等保存（fetch / save 呼び出し）。バックフィルや健全性チェックあり。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult dataclass を公開（target_date / fetch/save カウント / quality_issues / errors を保持）。
    - pipeline モジュールの概要実装: 差分取得、保存（jquants_client 経由）、品質チェック（quality モジュール）を行う方針を実装。
    - jquants_client を介した fetch/save の利用、バックフィルロジック、エラーと品質問題は収集して呼び出し元に伝搬する設計。
    - DuckDB のテーブル存在チェックや最大日付取得用ユーティリティを実装。

- その他
  - DuckDB を主要なオンディスク分析 DB として利用する設計（関数は DuckDB 接続を受け取る）。
  - ロガーを適宜使用し、情報・警告・例外ログを出力。
  - DB 書き込み時の冪等性（DELETE→INSERT など）とトランザクション制御（BEGIN/COMMIT/ROLLBACK）を採用。
  - 多くの関数でルックアヘッドバイアスを避けるために日付を外部から注入する設計（内部で date.today() を参照しない）。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- OpenAI API キーや各種シークレットは環境変数/ .env で管理する設計。ログ出力に意図せずシークレットが含まれないよう注意すること。

Known limitations / Notes
- raw_news.datetime は UTC で保存されている前提で実装。
- DuckDB の executemany は空リストを受け付けないため、空パラメータ時の分岐を行っている（互換性対策）。
- news_nlp/regime_detector の OpenAI 呼び出しは gpt-4o-mini と JSON Mode を前提にしており、将来の API 変更に注意が必要。
- jquants_client, quality モジュールの具体実装はこの差分に含まれない（外部依存）。ETL の動作にはそれらの実装が必要。
- 一部の SQL は DuckDB 固有のウィンドウ関数/ROW_NUMBER 等を利用している。別 DB に移植する場合は SQL の調整が必要。
- テストを容易にするため、OpenAI 呼び出しは module 内の _call_openai_api をパッチして差し替え可能。

Upgrade / Migration notes
- 環境変数（最低限）:
  - OPENAI_API_KEY（AI 機能を使う場合必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- DuckDB のデータファイル（デフォルト data/kabusys.duckdb）や監視用 SQLite（data/monitoring.db）等のパスは Settings で変更可能。
- データベースのスキーマ（prices_daily, raw_news, news_symbols, market_regime, ai_scores, raw_financials, market_calendar 等）が存在することを前提とします。初期導入時はスキーマ準備が必要です。

もし記載の項目で詳細な日付や追加のリリースノート（例: minor/patch リリース情報）を入れたい場合は、その情報を提供してください。
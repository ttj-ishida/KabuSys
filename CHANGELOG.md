CHANGELOG
=========

すべての変更は "Keep a Changelog" の書式に準拠して記載しています。  
初期リリースの内容はソースコードから推測してまとめています。

[詳細]: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-29
------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ を "0.1.0" に設定、パッケージ外部公開シンボルとして data/strategy/execution/monitoring を __all__ で指定。

- 設定/環境変数管理 (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して検出。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local が .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env のパースは以下の挙動に対応:
    - 空行・コメント（先頭 #）を無視。
    - export KEY=val 形式に対応。
    - クォートあり（シングル/ダブル）でのバックスラッシュエスケープ処理。
    - クォートなしでは '#' の直前が空白またはタブの場合に inline コメントとして扱う。
  - OS 環境変数を保護するため、既存キーは保護集合として扱い .env による上書きを制御。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - 必須環境変数取得のための _require を実装（未設定時は ValueError）。
    - 提供プロパティ例:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (KABU_API_PASSWORD)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token, slack_channel_id
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV; 有効値: development, paper_trading, live)
      - log_level (LOG_LEVEL; 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - is_live / is_paper / is_dev ヘルパー属性を提供。

- AI モジュール (kabusys.ai)
  - news_nlp (ニュースセンチメントスコア)
    - target_date に対するニュース収集ウィンドウ計算 (calc_news_window) を実装。
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI (gpt-4o-mini) に送信。
    - バッチ/チャンク処理: 1コールあたり最大 20 銘柄 (_BATCH_SIZE)。
    - 1銘柄あたり最大記事数・最大文字数制限: _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK。
    - JSON Mode を利用し、レスポンスを厳密にバリデーションして ai_scores テーブルへ書き込み（DELETE→INSERT の冪等処理）。
    - リトライと指数バックオフ: 429/接続断/タイムアウト/5xx を対象に _MAX_RETRIES 回のリトライ、失敗時は対象銘柄をスキップして継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - regime_detector (市場レジーム判定)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - マクロニュース抽出にはキーワードベースのフィルタ（日本・米国/グローバルのキーワード群）。
    - OpenAI (gpt-4o-mini) を用いた JSON 出力評価を実装。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコアは clip(-1.0, 1.0)、閾値でラベル判定。
    - 計算結果は market_regime テーブルへトランザクションを用いて冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。書込失敗時は ROLLBACK を試行して例外を伝播。
    - API 呼び出し失敗や JSON パース失敗に対する詳細なログとフォールバック実装。
    - テスト用に _call_openai_api を差し替え可能。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジックを実装（market_calendar テーブルを参照）。
    - 営業日判定/is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日ベース（土日休み）でフォールバック。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS) により無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新し、バックフィルと健全性チェックを実施。
  - pipeline / ETL
    - ETLResult データクラス (pipeline.ETLResult) を公開 (data.etl を介して再エクスポート)。
    - ETL の設計方針・定数（初期データ開始日、カレンダー先読み日数、デフォルトのバックフィル日数等）を定義。
    - テーブル存在チェック・最大日付取得ユーティリティを実装。
    - ETL 実行結果の to_dict() により quality_issues をシリアライズ可能に。
    - ETL は差分更新・保存（idempotent）・品質チェックを行う設計。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率を計算。NULL の扱いに注意した TR（true range）計算。
    - バリュー (calc_value): raw_financials から最新財務データを取得して PER/ROE を計算。EPS が 0/欠損の場合は None。
    - DuckDB のウィンドウ関数を活用し、date/code 単位での結果を返す。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 複数ホライズンを同時に処理、horizons のバリデーションを実装。
    - IC 計算 (calc_ic): ファクターと将来リターンのスピアマンランク相関を算出（有効レコードが 3 未満の場合は None）。
    - ランク変換ユーティリティ (rank): 同順位は平均ランクで算出。丸めによる ties 問題に対処。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。None 値は除外。
  - data.stats からの zscore_normalize を re-export（research パッケージにて）。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- （初期リリースのため修正履歴はなし）

Security, Safety & Behavior Notes
- AI 系 API（OpenAI）を利用する関数は api_key 引数を受け取り、引数未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗する。
- AI 呼び出しはリトライ・フォールバックを内蔵しており、API 失敗時にシステム全体が停止しないように設計（部分スキップ・スコア 0.0 フォールバック等）。
- .env 自動ロードはプロジェクトルート検出に依存し、配布後もカレントワーキングディレクトリに依存しないよう実装。
- データベース書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当の扱い）し、トランザクション管理と ROLLBACK を組み込み。DuckDB の executemany の制約（空リスト不可）を考慮した実装。

公開 API の主な関数 / クラス
- settings (kabusys.config.Settings のインスタンス)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.pipeline.ETLResult (および data.etl 経由での再エクスポート)

既知の制約・注意点
- DuckDB のバインド挙動（executemany に空リスト不可）に対するワークアラウンドが実装されているため、古い DuckDB バージョンを想定した実装が含まれます。
- 一部の設計方針として「datetime.today()/date.today() を参照しない」方針が徹底されているため、外部から明示的に target_date を渡す運用が前提です（ルックアヘッドバイアスの防止）。
- monitoring モジュールは __all__ に含まれるが、本 changelog の元となるコード断片には未掲示のため、実装詳細は別途確認が必要です。

開発者向けメモ
- テスト容易性のため、OpenAI 呼び出し部分（_call_openai_api）は unittest.mock.patch で差し替え可能に実装されています。
- 環境変数の必須チェックは Settings のプロパティで行われ、未設定時は ValueError で明示的に失敗します。CI/実行環境で必要な env を設定してください。

今後の提案（参考）
- monitoring モジュールの実装・公開 API の明記。
- strategy / execution 周りのエンドツーエンドテスト整備（実取引 API はモック化してテスト可能に）。
- より詳細な品質チェック（quality モジュール）のルール拡充と、ETL 実行時のアラート（Slack 連携など）の自動化。

--- 

この CHANGELOG はソースコードの記述から推測して作成した初期リリースノートです。追加の実装やリファクタリングが行われた場合は随時更新してください。
# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルは初期リリースの機能・設計上の決定や注意点をコードベースから推測してまとめたものです。

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境設定 / ロード機能 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、カレントワーキングディレクトリ (CWD) に依存しない実装。
  - .env/.env.local の読み込み順と上書きルール:
    - OS 環境変数 > .env.local (override=True) > .env (override=False)
    - OS 環境変数は protected として上書きされない。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env のパース実装:
    - コメント行、export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV 制約（development, paper_trading, live）および LOG_LEVEL 検証（DEBUG..CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- ニュースNLP / AI スコアリング (kabusys.ai.news_nlp)
  - score_news(conn, target_date, api_key=None)
    - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内の raw_news と news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) へバッチ送信してセンチメントスコアを算出。
    - バッチ処理: 最大 _BATCH_SIZE (20) 銘柄ずつ、一銘柄あたり最新 _MAX_ARTICLES_PER_STOCK（10）件・文字数トリム(_MAX_CHARS_PER_STOCK=3000)。
    - API レスポンスは JSON Mode を想定し、レスポンスのバリデーション・抽出ロジックを実装（_validate_and_extract）。
    - レスポンス・スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行。その他のエラーはスキップしフェイルセーフで継続。
    - DuckDB executemany の空リスト問題に対応した保護（空リスト時は実行しない）。
    - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを合成して日次レジームを判定（重み: MA 70%、マクロ 30%）。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI へ送信して macro_sentiment を算出（_score_macro）。
    - LLM 呼出しに対するリトライ・5xx/レート制限ハンドリングを実装。API失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアを clip(-1,1) し閾値で 'bull'/'neutral'/'bear' を決定。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出。

- 研究用ファクター / 特徴量探索 (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200_dev（200日MA乖離率）を算出。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR、ATR比率、20日平均売買代金、出来高比率などを算出。必要行数未満で None を返すフィールドあり。
    - calc_value(conn, target_date): raw_financials の最新財務データと価格から PER / ROE を算出（EPSなし/0のとき PER を None）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 指定営業日ホライズンに対する将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関 (IC) を計算。データ不足時は None。
    - rank(values): 平均ランクを返す（同順位は平均ランク、丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - kabusys.research.__init__ で主要関数を再公開、zscore_normalize を data.stats から再エクスポート。

- データ管理 / ETL / カレンダー (kabusys.data)
  - calendar_management:
    - 市場カレンダー管理（market_calendar テーブル）: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーデータが存在する場合はそれを優先し、未登録日は曜日ベースのフォールバックを行う（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新。バックフィル/健全性チェック実装。J-Quants クライアントを利用。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート）。
    - ETLResult は品質チェック結果（quality_issues）、取得/保存件数、エラー一覧等を保持し、to_dict() で辞書化可能。
    - 差分更新、バックフィル、品質チェック（quality モジュール）の呼び出し方針や設計をコード上で定義。

- ロギング・エラーハンドリング
  - 主要処理はログ出力を行い、API 呼び出し失敗時はフェイルセーフ（例: macro_sentiment=0.0、該当チャンクスキップ）で継続する設計。
  - DB 書き込みでの例外時は ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出力する。

Fixed / Behavior decisions
- ルックアヘッドバイアス対策
  - AI/研究関連の処理で datetime.today()/date.today() を直接参照しない実装を徹底。target_date を引数で受け取り、クエリは date < target_date（排他）や指定ウィンドウを用いて将来データを参照しないように実装。
- .env パーサーの堅牢性向上
  - 引用符内のエスケープ処理、export プレフィックス、コメント判定に関する細かいケースに対応。
- OpenAI API の堅牢な呼び出しとバリデーション
  - JSON レスポンスの前後に余計なテキストが混入するケースへ保険をかけたパース（最外側の {} を抽出して復元）を実装。
  - レスポンスが期待形式でない場合はログを出して当該チャンク/記事をスキップ。
- DuckDB 互換性対策
  - executemany に空リストを渡すと失敗する点に対応し、空時は実行をスキップするガードを実装。
- 安全な環境変数保護
  - .env のオーバーライド時に OS 環境変数を protected として上書きしない仕様を導入。

Security
- 機密情報（APIキー等）の扱い
  - OpenAI API キーは引数優先、未指定時は OPENAI_API_KEY を環境変数から取得する仕様。未設定時は明示的に例外を送出する箇所がある（誤操作防止のため）。

Notes / Known requirements
- AI 機能の利用には OpenAI API キー（OPENAI_API_KEY）または各関数の api_key 引数が必須。
- DuckDB にテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が存在することを前提とした処理が多数あるため、初期セットアップ（スキーマ作成・初期データ投入）が必要。
- デフォルトの DB パスは設定で変更可能（DUCKDB_PATH, SQLITE_PATH）。
- 一部外部 API（J-Quants、kabuステーション、Slack など）への接続ロジックはクライアントモジュール経由で想定されており、実行環境に合わせて認証情報やエンドポイントを設定する必要がある。

未実装 / 今後想定される改善点（コードから推測）
- PBR・配当利回りなどのバリューファクターの追加（calc_value 内に未実装コメントあり）。
- strategy / execution / monitoring の実装詳細（パッケージ公開先はあるが本スナップショットではソース不在の可能性あり）。
- テスト・モック用の抽象化（OpenAI 呼び出しは patch で置換可能な形になっているが、さらにインジェクションしやすい設計改善の余地）。

------------------------------------
訳注:
- 本CHANGELOGは与えられたコードベースの内容から実装意図・挙動を推測して記載しています。実際のリリースノートとして使用する際は、プロジェクトの実際の変更履歴やコミットログと照合してください。
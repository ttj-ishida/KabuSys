CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
すべての重要な変更点をここに記録してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

Added
- run_monitoring のポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能に（デフォルト 60 秒）。0 以下の値や不正値はデフォルトにフォールバックし、警告ログを出力するようにした。
- run_monitoring/run_execution 起動スクリプトで実行開始時にプロセス優先度を設定する仕組みを起動直後に行うように変更（set_process_priority("high") をデフォルト実行）。
- SystemMonitor / ExecutionEngine の終了ハンドリング強化（KeyboardInterrupt へのログ出力や DB 接続の確実なクローズ）。

Changed
- Settings の .env 自動ロード処理の説明・挙動を明確化（プロジェクトルート検出ロジック、.env と .env.local の読み込み優先度、OS 環境変数保護の挙動）。
- .env パーサーの挙動を改善（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱いを改善）。
- Paper Trading 実行時に使用する SQLite DB を本番 DB と完全に分離（KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使う）。
- OpenAI とのやり取り（ai.news_nlp）でバッチ処理、最大バッチサイズや各種クリップ・リトライ設定を導入。失敗時は個別チャンクをスキップして他チャンクへ影響を与えない設計に。

Fixed
- Settings.paper_fill_mode の検証を追加（有効値チェック、無効時は ValueError）。
- process_priority のプラットフォーム差分ハンドリングを明確化し、アクセス権限や未対応 OS の場合は警告ログを出すようにして強固にフォールバックするように修正。
- 各種ファクター / レポート計算処理（research、tools）でデータ不足時の安全な挙動（None 戻り、OperationalError の捕捉）を標準化。
- calc_score_weights が全銘柄のスコア合計 0 の場合に等金額配分へフォールバックするバグ回避。

0.1.1 - Unreleased
------------------
（将来の小さな修正・ドキュメント追加用）

0.1.0 - 2026-04-12
------------------

Added
- 初回公開リリース。以下の主要機能を搭載。
  - コア情報
    - パッケージメタ情報（kabusys.__version__ = "0.1.0"）。
  - 設定管理
    - kabusys.config: .env 自動ロード（.env / .env.local）、プロジェクトルート自動検出、環境変数取得ユーティリティ（Settings クラス、settings インスタンス）。
    - 多数の環境設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値（CPU/MEM/DISK）、LOG_LEVEL、KABUSYS_ENV など。
    - PAPER_FILL_MODE の導入と値検証（instant/partial/never/reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード抑止。
  - 起動スクリプト
    - run_execution: ExecutionEngine を構成・起動するエントリポイント。BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager の組み立て、RiskConfig のデフォルト値設定、paper_trading モード時の DB 分離をサポート。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL による間隔指定、監視 DB 初期化（init_monitoring_db）、DuckDB 接続の併用、例外耐性を備えたポーリングループ。
  - 監視・DB
    - monitoring_db 初期化呼び出し（init_monitoring_db）による監視テーブルの冪等初期化。
    - 監視ループは本番 sqlite_path を使用（環境に依らず本番 DB を参照する設計）。
  - ユーティリティ
    - utils.process_priority: プラットフォームに依存しないプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。Windows / POSIX(Linux/Darwin/FreeBSD) に対応し、権限不足や未対応 OS の場合はログを出してスキップ。
  - ポートフォリオ構築（Portfolio）
    - portfolio.portfolio_builder: select_candidates（スコア降順・同点時タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合は等配フォールバック）。
    - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap スケールダウン、cost_buffer による保守的見積り、単元株丸めロジックと残差配分アルゴリズム）。
    - portfolio.risk_adjustment: apply_sector_cap（既存保有のセクター露出計算と上限超過セクターの候補除外、"unknown" セクターは除外しない）、calc_regime_multiplier（bull/neutral/bear の乗数と未知レジームのフォールバック）。
  - 調査・リサーチ
    - research.factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL ベースの計算、ウィンドウ条件と欠損対処）。
    - research.feature_exploration: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（Spearman のランク相関による IC 計算）、rank、factor_summary（count/mean/std/min/max/median 計算）。
    - research パッケージは zscore_normalize を外部からエクスポート（kabusys.data.stats を利用）。
  - AI / ニュース NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む。主な設計:
      - ニュースウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）。
      - 銘柄ごとの記事集約、記事数 / 文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大チャンクサイズ 20 のバッチ送信、JSON Mode での厳密なレスポンス期待。
      - 429 / ネットワークエラー / 5xx 等に対する指数バックオフリトライ（最大 _MAX_RETRIES）。
      - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の部分書き換え（DELETE/INSERT による置換）で既存データ保護。
      - API キー未設定時は ValueError を送出。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成コマンドラインツール（--from / --to / --db オプション対応）。システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - レポートは SQLite DB のテーブル（system_status, trade_logs, risk_logs 等）を参照。データ不足やテーブル未存在時は N/A / 0 で扱う安全な実装。
  - DuckDB 統合
    - DuckDB を分析用途に導入（prices_daily, raw_financials, ai_scores などの集計に使用）。executemany に関する注意点やパラメータチェックに配慮。
  - ロギングと例外処理
    - 各コンポーネントで適切な logging（info/debug/warning/exception）を追加し、外部 API 呼び出しや DB 操作の失敗をスキップ/フォールバックしてシステム全体の堅牢性を確保。

Changed
- パッケージ公開前のコード整理とモジュール公開 API の整備（portfolio、research、ai の __all__ エクスポート整理）。
- SQL クエリや集計ロジックにおける NULL / データ不足時の安全ガードを追加。

Fixed
- feature_exploration.rank の同位順位処理を平均ランクに戻すことで tie の扱いを明確化。
- factor_research のウィンドウ境界や行数チェック（MA/ATR の要件行数チェック）により不十分なデータでの誤った数値返却を防止。
- paper_verification_report の P95 計算で空リスト時に None を返すよう修正。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いは引数優先で環境変数参照とし、未設定時は明示的にエラー扱いとして誤操作による無意識の API 呼び出しを防止。

Notes
- 本 CHANGELOG はコードベースの実装内容から推測して記載しています。内部 API の振る舞いや将来のリファクタリングにより実装詳細が変わる可能性があります。質問や不明点があれば該当モジュール名を指定して問い合わせてください。
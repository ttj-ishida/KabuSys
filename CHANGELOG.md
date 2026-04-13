CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

Added
- 基本アプリケーション初期版を追加。
  - パッケージのバージョンを kabusys.__version__ = "0.1.0" として定義。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager の組み立てと run_session 起動。
    - DuckDB と SQLite（本番またはペーパートレード用に切替）への接続処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - paper_trading 環境では PAPER_TRADING 用専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
- 監視エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB の接続管理、例外時のログ出力と安全なクローズ処理を実装。
- 設定管理
  - config.Settings を追加。
    - .env/.env.local の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を探索）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を上書きしない保護（protected）ロジックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 必須変数取得用 _require、各種環境変数の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - DB パス、PID / KILL フラグパス、各リソース閾値（CPU/MEM/DISK）など多くの設定プロパティを提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合はフォールバックで等金額）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を考慮して候補から除外する機能（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジック。
    - 価格欠損時のスキップ、既存ポジションとの差分発注を計算。
- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率を計算。
    - calc_volatility: ATR(20) / 相対 ATR / 20 日平均売買代金 / 出来高比を計算。
    - calc_value: raw_financials と prices_daily を使った PER / ROE の計算（target_date 以前の最新財務データを利用）。
    - DuckDB SQL による効率的なウィンドウ集計を実装。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を効率的に取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量とランク化ユーティリティを提供。
    - 外部依存（pandas 等）なしで標準ライブラリのみで実装。
- AI ニュース NLP
  - ai.news_nlp
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事集約、銘柄ごとのトリム（記事数・文字数上限）を実装。
    - 最大バッチサイズ、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）、部分成功時のテーブル差分置換（DELETE→INSERT）等のフェイルセーフ設計。
    - OpenAI API キー未設定時は明確な ValueError を送出。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows/Linux(Mac/FreeBSD) を吸収する優先度設定。権限不足や未対応 OS の場合は警告して安全にスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へプロセスをピンニング（エラー時は警告してスキップ）。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出（閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）をサポート。
    - 不足データやテーブル未存在時のフォールバックを実装。
- パッケージ公開用 __all__ の整理
  - portfolio/research モジュールからのエクスポートを整備。

Changed
- 設定ロードの優先順位を明確化: OS 環境変数 > .env.local > .env。自動ロードはプロジェクトルートが見つからない場合はスキップ。
- .env パーサの堅牢化:
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを改善。
- Monitoring と Execution の DB 接続方針を明記:
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計。
  - 実行（run_execution）は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と完全分離。

Fixed
- 環境変数のバリデーション強化:
  - PAPER_FILL_MODE の有効値チェックを追加し、不正な値で ValueError を返すように。
  - KABUSYS_ENV / LOG_LEVEL の値検査を追加。
- calc_score_weights: スコア合計が 0 の場合は等金額配分へフォールバック（警告ログ）。

Security
- OpenAI API キーは明示的に引数または環境変数で供給する仕様とし、未設定時に明確な例外を出すことで誤設定に起因する無駄な API 呼び出しを防止。

Notes / Known limitations
- position_sizing の価格欠損時の挙動についてコメントに TODO を残しており、将来フォールバック価格（前日終値や取得原価）の導入を検討。
- ai.news_nlp の実装は API レスポンス検証や部分的な DB 書き込み保護を行うが、外部 API の仕様変更に対する追加の互換性テストが必要。
- run_monitoring の MONITOR_POLL_INTERVAL は 0 以下の値を安全に扱うためにデフォルトへフォールバックする実装になっている（time.sleep への負値渡し回避）。

当 changelog はソースコードの中身から推測して作成しています。実際のリリースノートと差異がある場合は、必要に応じて編集してください。
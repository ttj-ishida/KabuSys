CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

未リリース
---------

（なし）

0.1.0 - 2026-04-25
-----------------

初回公開リリース。

追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 実行用スクリプト / デーモン類
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する実行フローを実装（MockBrokerClient の利用は BrokerClientFactory 側で切り替え）。
    - 起動時にプロセス優先度を設定（high）し、PID ファイルを扱う。
    - プロセス停止はプロジェクトルートの data/stop_requested.flag を検知して行う（安全な停止フロー）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ用スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 初期化（monitoring テーブル等）を行う。Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 設定管理
  - config.py
    - Settings クラスを実装。環境変数をプロパティで取得する統一 API を提供。
    - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。`.env` と `.env.local` を読み込み、OS 環境変数を保護する仕組みを実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - env 値検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証、PAPER_FILL_MODE のバリデーション等）を実装。
    - データベースパス、PID/kill フラグパス、監視しきい値等のプロパティを提供。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで初期 .env を作成・更新する CLI を追加。
    - J-Quants トークンや kabu API パスワード等のシークレット入力をサポート。既存 .env の読み込み、確認、上書き保存機能を備える。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数の有無、KABUSYS_ENV の検査、LOG_LEVEL、DB パスの親ディレクトリ確認、config/*.yaml の存在/パース検証等）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - PyYAML 未導入時は YAML 内容検証をスキップして警告を出す。
    - 本番 (live) 用のガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
- ロギング / プロセス周りユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで使える統一的なログ設定関数 `setup_logging` を実装。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保管）をルートロガーに設定。既存ハンドラの重複設定を防止するため既存ハンドラをクリアする。
    - LOG_DIR / LOG_LEVEL の環境変数または引数で挙動を制御。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定機能を実装（Windows / POSIX に対応）。失敗時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティも追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定関数 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap（既存ポジション評価・当日売却予定の除外対応）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知はフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - allocation_method (`risk_based`, `equal`, `score`) に基づく株数算出を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリング）、コストバッファ考慮、残余キャッシュ配分の端数処理などを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率・注文成功率・送信率・API レイテンシ（P95）等を算出して PASS/FAIL 判定を出力する CLI を追加。
    - デフォルトの閾値（稼働率 99%、注文成立率 90% 等）を定義。期間フィルタ（--from/--to）対応。
- 研究用ファクター計算基盤
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity 等）を計算するための骨組みを導入。prices_daily / raw_financials テーブルを参照する設計。
    - モメンタム関連の定数や P95 計算等のユーティリティを含む（calc_momentum 等の関数群の実装を開始）。
- パッケージエクスポート
  - portfolio パッケージの __init__ を整備して主要関数をエクスポート。

変更 (Changed)
- なし（初回リリースのため変更履歴はありません）。

修正 (Fixed)
- なし（初回リリースのため修正履歴はありません）。

注意事項 / 実装上の補足
- .env の自動ロードはプロジェクトルートを探索して行われるため、配置や配布後の動作が安定する設計。ただし自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数を提供しています。
- ログは標準出力（stdout）へも出るため、cron/Task Scheduler などからの起動時にログをキャプチャしやすくしています。ファイル出力に失敗した場合は console のみで継続します。
- run_monitoring/run_execution は stop フラグファイルや PID ファイルを用いる簡易なプロセス制御を行います。運用時は data ディレクトリの取り扱いに注意してください。
- 一部機能（研究用ファクター計算や BrokerFactory の具体実装など）は内部で別モジュールに依存します。環境準備（必要なライブラリや config/*.yaml、.env の設定）を行ってから起動してください。

将来の改善案（非網羅）
- ファイル単位、銘柄単位での単元情報（lot_size）を stocks マスタ等から取得する拡張。
- price の欠損時のフォールバックロジック（前日終値や取得原価など）。
- factor_research の完全実装と DuckDB によるより多くのファクター指標の出力。
- ログの構造化（JSON 出力）や監視イベントの外部通知（LINE / Webhook）の強化。
CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-11
------------------

Added
- 基本リリース: KabuSys v0.1.0 を公開。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成をサポート（MockBroker を含む想定）。
    - Engine の起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
    - OrderRepository、OrderManager、RiskManager（デフォルト構成値を含む）、Reconciler を組み合わせて ExecutionEngine を起動。
    - デーモンスレッドでセッションを実行し、停止フラグ検知で安全に停止する制御を実装。

- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring DB の分離方針）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。KeyboardInterrupt にも対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - .env ファイルの自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env のパースロジックを強化（export プレフィックス、クォート内のエスケープ、コメントの扱いなど）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを導入し、環境変数から各種設定値（DB パス、API トークン、監視閾値、環境種別など）を取得する統一 API を提供。
    - Paper Trading 固有設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH）に対応し妥当性チェックを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力をサポートし、.env をテンプレート形式で書き出す機能を提供。
    - 既存 .env の読み込みと Enter で既存値を再利用する UX を実装。

  - validate_config.py
    - 起動前に設定（環境変数・config/*.yaml）を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config YAML の存在とパース検証（PyYAML が利用可能な場合）などを実装。
    - --strict モードで警告を失敗扱いにするオプションを提供。
    - 本番用のガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を警告として提示。

- ロギング/実行ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。
    - stdout 出力用の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラを安全にクリアして二重設定を防止。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows: priority class, POSIX: nice）と CPU affinity を設定するユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - buy シグナルの候補選定（スコア降順、タイブレークルール）を実装。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合等金額にフォールバックする警告あり。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を追加。既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を追加。デフォルトで bull/neutral/bear に対して 1.0/0.7/0.3 を返し、未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - ポジションサイズの計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based モード: 損切り幅・リスク許容率からベース株数を計算、単元（lot_size）で丸め。
    - equal/score モード: 重み・max_utilization を使った配分、1 銘柄上限（max_position_pct）を適用。
    - aggregate cap（利用可能現金を超える場合はスケールダウン）と端数処理（lot 単位での再配分）を実装。
    - cost_buffer を考慮したコスト見積りで保守的に計算。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率(send rate)、API レイテンシ（avg/max/P95）などを算出して判定（PASS/FAIL）を出力。
    - デフォルトの閾値を定義（稼働率 99% / 成功率 90% / 送信率 95% / P95 レイテンシ 200 ms）。
    - --from/--to/--db オプションで期間・DB を指定可能。DB が見つからない場合はエラーメッセージを出力。

- research
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム、Value、Volatility、Liquidity の方針と計算レンジ）を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算を行う設計。関数 calc_momentum の実装開始（ファイル末尾で切れている部分あり）。

Changed
- 初期リリースのため、既存ライブラリの整理とエントリポイント（__main__ での実行）を統一。

Fixed
- N/A（初期リリースのため既知の修正はなし）

Removed
- N/A

Notes / Implementation details
- 監視ループと実行エンジンは stop_requested.flag を用いて外部から停止を指示できる設計。
- .env のロード順は OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
- 設定チェックツールは PyYAML の有無に応じて YAML 検証をスキップする（インポート失敗時に警告）。
- ロギングは stdout を優先し、cron/タスクスケジューラでのリダイレクトを想定して stderr ではなく stdout を使用。
- 一部ファイル（research/factor_research.py）の実装は継続作業を前提としており、今後のリリースで完了予定。

Contributing
- バグ報告・機能要望は issue を立ててください。プルリクエストにはユニットテストと簡潔な変更説明を添えてください。
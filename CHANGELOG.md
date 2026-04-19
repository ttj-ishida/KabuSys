CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
リリースの優先度は安定性・運用性・機能追加の順です。

Unreleased
----------

- なし

v0.1.0 - 2026-04-19
-------------------

Added
- 基本アプリケーション骨格を実装
  - パッケージ情報:
    - kabusys.__version__ = 0.1.0
    - エクスポートモジュール群を定義（data, strategy, execution, monitoring）

- 実行スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag により制御。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して起動（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続を初期化し、例外はログに記録してポーリングを継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（data/paper_trading.db）を使用し MockBrokerClient を利用する想定で本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止は data/stop_requested.flag と execution.pid を用いる。停止検知でエンジンに停止を通知してシャットダウン。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててスレッドで実行。

- 環境 / 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの考慮などに対応。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV・LOG_LEVEL の検証、各種デフォルトパスを定義。

  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。
    - 機密項目はマスク表示、選択肢やデフォルトを提示して安全に .env を生成。
    - .env 書き出しテンプレートを提供（生成物は Git にコミットしない注意書き）。

  - validate_config.py
    - 起動前に環境変数・config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば実行）、本番環境での追加ガード（LINE 通知設定や Kill Switch 設定）等の検証を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートされたファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベルの解決順とログディレクトリ解決順を文書化。

  - utils/process_priority.py
    - プラットフォームを吸収するプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux, Darwin, FreeBSD）での優先度設定を抽象化（Windows の優先度クラス、POSIX の nice 値）。
    - アクセス権がない環境などで失敗しても警告ログを出して安全にスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（存在しない・許可されない環境は警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - candidate 選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告ログ。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - unknown セクターはセクター上限チェックの対象外にする挙動や、未定義レジーム時はフォールバック 1.0 を返して警告ログを出力する仕様を明記。

  - portfolio/position_sizing.py
    - position size を計算する calc_position_sizes を実装。
    - allocation_method は "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差の分配アルゴリズム等を実装。
    - 価格欠損時はスキップしてログ出力。

  - portfolio パッケージ __init__ で主要関数を公開。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から各種指標を抽出して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）し、Pass/Fail を判定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - P95 計算を独自実装し、DB の欠損テーブルに対しては N/A を扱う防御的実装。

- 研究用ファクタ計算 (研究モジュール)
  - research/factor_research.py
    - DuckDB を用いたモメンタム等のファクタ計算の骨組みを追加（モメンタム指標: 1M/3M/6M リターン、MA200乖離など）。（calc_momentum の実装開始を含む。）
    - 設計方針とスキャン期間等の定数を定義。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 運用上の注意
- .env は絶対にソース管理にコミットしないでください（config_setup.py のヘッダにも明記）。
- 本番運用時は KABUSYS_ENV=live の設定に注意してください。validate_config の実行を推奨します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）。
- run_monitoring は監視情報を本番 sqlite_path に書き込む設計です。開発やペーパートレード時に監視データを分離したい場合は運用ルールを再検討してください。
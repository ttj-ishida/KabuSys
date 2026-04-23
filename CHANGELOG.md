CHANGELOG
=========

すべての顕著な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。
バージョン番号は src/kabusys/__init__.py の __version__ を基準にしています。

Unreleased
----------

- なし（まだリリースされていない変更があればここに記載）

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース: KabuSys 基本機能群を追加。
  - 実行／監視ランナー
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を想定した分離動作をサポート。
      - エンジンはスレッドで実行され、 data/stop_requested.flag による外部停止が可能。PID ファイル出力に対応。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、初期ポートフォリオ値をブローカーから取得して利用。
    - run_monitoring.py: SystemMonitor のポーリング起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全終了。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を明確化。
  - 設定管理
    - config.py: 環境変数・.env ロード、Settings クラスを提供。
      - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local、OS 環境変数優先）。
      - .env の詳細なパース実装（export プレフィックス、クォート内エスケープ、インラインコメント処理等）。
      - 各種設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, paper_trading 用設定等）とバリデーションを提供。
    - config_setup.py: 対話式 .env ウィザードを追加（既存 .env 読み込み、secret マスク表示、保存）。
    - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数のチェック、config/*.yaml の存在・パース検証、production 向けガードなど）。--strict オプションで警告を失敗扱いに可能。
  - ポートフォリオ構築（純関数モジュール）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - portfolio/risk_adjustment.py
      - セクター上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py
      - 発注株数判定ロジック（risk_based / equal / score）、単元丸め（lot_size）、aggregate キャップ（available_cash によるスケールダウン）、コストバッファ考慮などを実装。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定を提供。
      - stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を組み合わせて設定。
      - LOG_DIR/LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバックを実装。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度・CPU affinity 設定ユーティリティを追加（psutil を利用、Windows/Linux/macOS 対応のフォールバック処理）。
  - モニタリング DB 初期化
    - monitoring/monitoring_db.py（起動スクリプトから利用される初期化関数）を想定し、起動時に監視テーブルの存在を保証する仕組みを組み込み。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計し PASS/FAIL 判定を出力。
      - デフォルト DB は data/paper_trading.db、コマンドラインで期間・DBパス指定可能。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加（DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計）。
      - モメンタム指標（1M/3M/6M リターン、MA200 乖離）等の計算ロジックを準備（注: 実装の一部が継続実装を想定）。
  - パッケージ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- ログ出力ポリシー: ログは標準エラーではなく標準出力（stdout）に出力するように設計。cron／スケジューラ環境でのリダイレクトを想定。
- .env 自動読み込みの挙動: OS 環境変数を保護しつつ .env/.env.local の読み込みを行う。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

Fixed
- .env パーサーの堅牢化: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどを改善。
- ログディレクトリ作成失敗時のフォールバックを実装（ファイルハンドラ作成失敗時はコンソール出力のみで継続）。
- プロセス優先度設定の失敗を警告ログで扱い、アクセス権限のない環境でも安全に起動するように改善。

Security
- シークレット値（トークン・パスワード）は .env ウィザードでマスク表示するよう配慮（ファイルへの書き込み時にも注意書きを追加）。

Notes / Known issues
- run_monitoring の設計により、監視コンポーネントは KABUSYS_ENV に依存せず常に sqlite_path（本番想定）を参照します。テストやローカルで監視を実行する場合は sqlite_path を明示的に書き換えるか、監視用 DB を別途用意してください。
- research/factor_research.py はファクター計算の主要なロジックが実装されていますが、データスキャン境界やスキャン日数バッファなどのチューニングと追加テストを要します。
- ExecutionEngine / BrokerClientFactory 等の実行時の外部依存（ブローカー API、psutil、duckdb、PyYAML 等）は環境に応じたインストール・設定が必要です。validate_config.py を利用して起動前に設定を確認してください。

ライセンス
- 本プロジェクトのライセンス情報はリポジトリ内の LICENSE ファイルを参照してください。
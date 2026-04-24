Changelog
=========

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

Added
- 監視・実行・設定関連の起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag ファイルで制御。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient 経由で動作を分離。
- 設定・検証・ウィザードの CLI を追加
  - config_setup.py: .env を対話式に生成・更新するウィザードを提供。シークレット項目のマスク表示、既存 .env の読み込み、確認後の保存をサポート。
  - validate_config.py: .env と config/*.yaml の簡易整合性チェック CLI。--strict オプションで警告を FAIL 扱いにできる。PyYAML が無い場合は YAML 検証をスキップして警告を出力。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB を解析して稼働率・注文成功率・レイテンシ等のレポートを生成。期間指定オプション（--from / --to）、DB パスの上書きオプション（--db）対応。各指標の合格/不合格判定基準を定義。
- ポートフォリオ構築関連の純粋関数モジュールを追加（DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数計算ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積。
- ログ・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテーションのファイルハンドラをルートロガーへ設定。LOG_LEVEL / LOG_DIR / app_name に基づく解決、ディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity を最初の N コアへ固定する set_cpu_affinity も提供。
- 環境設定管理を強化
  - config.py: .env 自動読み込み機構（.env → .env.local の順、OS 環境変数を保護）と、export 形式やクォート、バックスラッシュエスケープ、インラインコメントへの対応を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。各種設定値（DB パス、ログレベル、paper_trading 関連、監視閾値など）のプロパティを提供。
  - .env の読み込みルール: OS 環境変数を保護する protected 引数を利用した上書き制御。
- Execution コンポーネントの組み立て（ファクトリ / マネージャ / エンジン）
  - run_execution 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て起動するワークフローを定義。RiskManager の既定設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker, max_drawdown 等）を追加。
- 監視 DB 初期化ユーティリティを呼び出し（init_monitoring_db）し、監視テーブルの冪等的保証を実装。
- パッケージメタ
  - __version__ を "0.1.0" に設定。

Changed
- ログの出力先設計を統一
  - stdout を StreamHandler に使用（stderr ではなく）、ファイルハンドラは日次ローテーションで 30 日保持。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する挙動に標準化。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いを改善し、より現実的な .env フォーマットに対応。

Security
- シークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン）は config_setup の対話で入力時にマスク表示。

Notes / Known issues
- run_monitoring は「環境にかかわらず」settings.sqlite_path（本番想定の monitoring.db）を使用する設計です。開発環境で分離した DB を利用したい場合は設定の見直しが必要です（意図的な設計のため注意）。
- factor_research モジュール（research/factor_research.py）は追加済みですが、実装の一部が未完（ファイル末尾が途切れている）であり、現時点では実験的・開発中です。
- paper_trading の DB はデフォルトで data/paper_trading.db に分離されますが、PAPER_TRADING_SQLITE_PATH により上書き可能です。
- validate_config の YAML 検証は PyYAML の有無に依存します（未インストール時はスキップして警告）。

----------------------------------------

[0.1.0] - 2026-04-24
--------------------
Added
- 初回リリース公開: 基本的な自動売買フレームワークのコア機能を実装。
  - 起動スクリプト: run_monitoring, run_execution
  - 設定管理: config.py（自動 .env 読み込み、Settings クラス）
  - 設定支援ツール: config_setup（.env ウィザード）、validate_config（検証 CLI）
  - ログ/プロセスユーティリティ: utils/logging_setup, utils/process_priority
  - ポートフォリオ構築ライブラリ: portfolio モジュール（候補選定、配分、リスク制限、ポジションサイズ計算）
  - Paper Trading 検証レポート: tools/paper_verification_report
  - Execution コンポーネントの初期組み立て（BrokerClientFactory, ExecutionEngine との統合箇所）
  - 監視 DB 初期化（init_monitoring_db）の呼び出しを起動時に実行

Changed
- パッケージ公開バージョンを 0.1.0 に設定。

Fixed
- n/a（初回リリースのため既知の不具合は上記 Known issues を参照）

Security
- n/a

----------------------------------------

補足
- CLI のエントリポイントはモジュール実行（python -m kabusys.<module>）を想定しています（各ファイルに if __name__ == "__main__": ブロックあり）。
- 各種環境変数、デフォルトパス、動作例はソース内ドキュメントコメント（docstring）に記載されています。設定・デプロイ時は validate_config と config_setup を併用して事前確認することを推奨します。
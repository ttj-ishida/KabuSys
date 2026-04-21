Keep a Changelog に準拠した CHANGELOG.md（日本語）
=================================

すべての変更は主にコードベースからの推測に基づき記載しています。実際の変更履歴と差異がある場合があります。

Unreleased
---------
- （なし）

0.1.0 - 2026-04-21
-----------------
Added
- 初期リリース相当の主要機能を追加。
  - 実行エントリ
    - run_execution.py: ExecutionEngine 起動スクリプト（デーモン的に実行、停止フラグ監視、paper_trading 時は専用 DB 使用）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔変更可、停止フラグ検知で終了）。
  - 設定関連
    - config.py: .env 自動読み込み（プロジェクトルート検出）、詳細な .env パース（クォート、export プレフィックス、インラインコメント、エスケープ対応）、設定値検証（KABUSYS_ENV, LOG_LEVEL 等）を提供する Settings クラス。
    - config_setup.py: 対話式 .env 作成・更新ウィザード CLI を提供。
    - validate_config.py: 起動前の設定検証 CLI（必須環境変数チェック、YAML ファイル検証、パス存在チェック、本番時の追加警告など）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選別（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）、レジームに応じた投下倍率（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score、lot_size による丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）。
  - 監視・実行インフラ
    - monitoring モジュール向けの DB 初期化呼び出し（init_monitoring_db を実行して監視テーブルの冪等初期化を保証）。
    - 実行用 BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler などの組立て（エンジン起動時に PID 管理・停止フラグ対応）。
  - ユーティリティ
    - utils/logging_setup.py: stdout ストリームと日次ローテートファイルハンドラの統合ロギングセットアップ。ログディレクトリ作成失敗時のフォールバックをサポート。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定。psutil の例外を扱い安全にスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト（稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定）。
  - リサーチ（骨組み）
    - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格。モメンタムや MA200 乖離、ATR、出来高指標等の計算設計を実装予定（関数インタフェースと定数定義を含む）。

Changed
- .env の読み込み順序と保護ルールを明確化。
  - OS 環境変数を優先（上書き保護）。
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。
  - .env.local は .env の上書きとして扱う（ただし OS 環境変数は保護）。
- run_monitoring/run_execution の設計
  - run_monitoring は KABUSYS_ENV に関わらず監視用に本番 sqlite_path を使用する方針を明示（運用上の設計決定）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用することで本番 DB と分離。

Fixed
- 環境変数パースの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善して .env の柔軟性と安全性を向上。
- MONITOR_POLL_INTERVAL の解釈を堅牢化（run_monitoring._get_poll_interval）
  - 無効値（0 以下や変換不能）時にデフォルト（60 秒）へフォールバックし、ログに警告出力。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラをスキップし、標準出力のみで継続するよう堅牢化。
- process_priority: 未サポート OS や権限不足時に警告を出して処理継続するよう改善。

Security
- .env ファイルを絶対に Git に含めないことをドキュメント化（config_setup のヘッダコメント）。
- config._require による必須環境変数チェックで不足時に早期にエラーを出すことで、秘匿情報の未設定を検出。

Performance
- position_sizing のスケーリングロジックで残余キャッシュを活用してロット単位で追加配分する（小さい丸め誤差を抑制し資金配分を効率化）。

Documentation / CLI
- config_setup と validate_config による対話式ウィザードと事前検証 CLI を追加。運用前チェックの自動化をサポート。
- tools/paper_verification_report はコマンドライン引数（--from/--to/--db）に対応。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等をフォールバックする旨の TODO コメントあり。
- portfolio/position_sizing:
  - lot_size は現状グローバル固定（例: 100）。将来的に銘柄別 lot_map に拡張する予定（TODO コメント）。
- research/factor_research.py:
  - ファイル末尾が断片的（calc_momentum の途中で切れている）であり、実装が未完了・継続中であることを示唆。
- その他、いくつかのモジュールは外部依存（psutil, duckdb, PyYAML 等）に依存しており、環境により機能制限や警告が発生する可能性あり（validate_config で警告出力するよう実装済み）。

Notes
- バージョンはパッケージ __init__.py の __version__ = "0.1.0" に合わせています。
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は適宜修正してください。
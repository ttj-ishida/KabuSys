CHANGELOG
=========

すべての注目すべき変更履歴を記録します。本プロジェクトは「Keep a Changelog」形式に従います。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Removed, Security 等）でグループ化します。
- バージョンごとに日付を付与します。

Unreleased
----------
（現在のリポジトリ状態に基づく暫定メモ。次回リリースで確定してください。）

- ドキュメント・コード整備:
  - モジュール間の責務分離を強化（設定、ログ、プロセス優先度、ポートフォリオ構築、ポジションサイズ計算、リスク調整、リサーチ、ツール群、実行/監視スクリプト）。
  - CLI ユーティリティ（設定ウィザード・設定検証・Paper Trading レポート）の操作性改善。
- 安全性・運用性:
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil ベース、Windows / POSIX 対応、権限不足時は警告でスキップ）。
  - ログ出力を統一する setup_logging を導入（stdout ストリームと日次ローテーションファイルハンドラを設定、ログディレクトリ自動作成、ファイルハンドラ失敗時はコンソールのみで継続）。
  - 停止フラグ / PID ファイルを利用した安全な起動・停止処理（run_execution, run_monitoring）。
- Paper Trading 分離:
  - Paper Trading 環境では専用 SQLite（data/paper_trading.db デフォルト）を使用するよう明確化。MockBroker の利用を想定。
- 監視:
  - SystemMonitor をポーリングする監視ループ（MONITOR_POLL_INTERVAL 環境変数で上書き可能、デフォルト 60 秒）。
  - 監視 DB 初期化を起動時に行う処理を追加（init_monitoring_db 呼び出し）。
- ポートフォリオ構築:
  - 候補選定（select_candidates）、等重み・スコア重み算出（calc_equal_weights / calc_score_weights）、セクター上限の適用（apply_sector_cap）、レジームによる投下資金乗数（calc_regime_multiplier）、ポジションサイズ算出（calc_position_sizes）を純粋関数群として実装。
  - position sizing は等金額 / スコア / リスクベースの配分方式をサポートし、単元株（lot_size）で丸めるロジック、aggregate cap によるスケーリング、コストバッファ考慮を実装。
- リサーチ:
  - DuckDB 接続を受け取ってファクター計算を行う骨組み（momentum, value, volatility, liquidity 指標設計方針）を追加。将来的なファクター計算の拡張に対応する設計。
- ユーティリティ:
  - .env 自動ロード機能の実装（プロジェクトルート検出: .git / pyproject.toml を基準）。.env と .env.local のロード順序（OS 環境変数が優先、.env.local は上書き）を実装。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - 環境変数取得のラッパー（Settings クラス）を提供し、型変換・妥当性検査を行うプロパティ群を実装（env / log_level の許容値チェック、paper_fill_mode の検証等）。
- レポート:
  - Paper Trading 向け検証レポート生成スクリプトを追加（稼働率 / 注文成功率 / 送信率 / レイテンシ P95 等を算出、閾値判定で PASS/FAIL を出力）。

0.1.0 — 2026-04-18
-------------------

Added
- 初回リリース相当の機能群を導入。
  - 実行系:
    - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV に応じて本番 DB / paper_trading DB を切り替え、BrokerClientFactory を用いてブローカークライアントを生成。スレッドでエンジンを実行し、停止フラグで安全に停止可能。
    - run_monitoring.py: SystemMonitor をポーリングする監視ループ。MONITOR_POLL_INTERVAL により間隔を制御。停止フラグ検知・例外ログ・リソースクローズを実装。
  - 設定管理:
    - config.py: .env 自動読込、プロジェクトルート検出、.env パース、Settings クラス（環境変数プロパティ）を実装。
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI。
    - validate_config.py: 起動前検証 CLI。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース（PyYAML 未導入時は警告）および本番向けガードチェック（LINE 通知、Kill Switch 設定）を提供。--strict モードをサポート。
  - モジュール:
    - portfolio: 候補選定、重み算出、ポジションサイズ算出、セクター上限、レジーム乗数などポートフォリオ構築ロジックを実装。数値丸め・上限・スケーリング・ログ出力を考慮。
    - research: ファクター計算モジュール（DuckDB を用いる設計）。モメンタム等の指標設計を追加（calc_momentum の骨組み）。
    - tools: paper_verification_report.py を追加。Paper Trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ等の指標を算出して判定レポートを出力。閾値はデフォルトで定義（稼働率 99%、成功率 90% 等）。
    - monitoring: 監視 DB 初期化ユーティリティを呼び出す導線を実装（init_monitoring_db の利用）。
    - execution: OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine 等の起動時組み立てフローを run_execution に統合（RiskConfig のデフォルト値を設定、初期ポートフォリオ値をブローカーから取得）。
  - utils:
    - logging_setup.py: ルートロガー設定ユーティリティ（StreamHandler を stdout に設定、TimedRotatingFileHandler 日次ローテーション、ログディレクトリ自動作成、既存ハンドラクリア）。
    - process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティ（Windows / POSIX の差分吸収。失敗時は警告で継続）。
  - パッケージメタ:
    - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースにつき過去の変更は無し。コード内に運用上の安全設計が反映されている点を明記）
  - 環境依存処理は Settings 経由に集約し、デフォルト値と妥当性チェックを追加。
  - .env 自動ロード時に OS 環境変数を保護するため protected set を使用して .env.local を上書き可能にした。

Fixed
- （既知のバグ修正履歴は無し。堅牢性を高めるための例外処理や警告出力を各所に追加）
  - run_monitoring/run_execution のループでの例外ハンドリングを追加（ログ出力して次回ポーリング・再試行へ）。
  - ログハンドラ設定時に既存ハンドラを flush/close してから削除することで二重出力を回避。

Security
- 秘密情報取り扱い:
  - config_setup のウィザードでシークレット項目（J-Quants トークン、Kabu API パスワード）をマスク表示し、.env のコミット禁止を README/コメントで明記。
  - Settings._require により必須環境変数未設定時に ValueError を送出し、起動前に明示的な確認を促す。

Notes / 運用上の留意点
- Paper Trading と Live の DB は厳密に分離されるように設計されています（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。
- run_monitoring は KABUSYS_ENV にかかわらず「本番（監視）用 sqlite_path」を使用する設計になっています。監視データは本番 DB に統合して収集する想定です。
- process_priority の設定は環境・権限に依存します。権限不足や未対応 OS では警告を出してスキップします。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布パッケージ環境等）。
- config/*.yaml のパース検証には PyYAML が必要です。未インストール時は警告を出して検証をスキップします。

参考: 環境変数の主な一覧（デフォルト値はコード内参照）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- MONITOR_POLL_INTERVAL — default: 60（秒）
- PAPER_FILL_MODE — default: instant（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — default: 0

今後の TODO（コードから推測）
- research.calc_momentum 等のファクター実装完了・テスト追加。
- ブローカークライアント抽象化のユニットテスト・モック整備。
- ストラテジー/実取引の統合テスト・シミュレーションツールの充実。
- ログ・メトリクスの収集（Prometheus 等）やアラート（LINE 以外）の拡張。

配布・リリース
- これが初期の機能セットとして 0.1.0 を想定しています。開発・試験運用を通じて次バージョンでバグ修正・機能追加を行ってください。
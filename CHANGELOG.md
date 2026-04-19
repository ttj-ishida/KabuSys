CHANGELOG
=========

すべての重要な変更は本ファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]

[0.1.0] - 2026-04-19
--------------------

Added
- 基本パッケージ初期実装を追加（初期リリース）。
  - パッケージバージョン: __version__ = 0.1.0 (src/kabusys/__init__.py)
- 起動用スクリプトを追加。
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db）を使用する。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止可能。
    - デーモンスレッドで ExecutionEngine を実行し、PID ファイルをサポート。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化含む）。
    - DuckDB との接続サポート、停止フラグ検出で優雅に終了。
- 設定管理と自動 .env 読み込み（src/kabusys/config.py）
  - プロジェクトルートを .git / pyproject.toml から探索して .env/.env.local を自動読み込み（テスト用に無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - .env パーサは export 形式、クォート（シングル/ダブル）やエスケープ、インラインコメントに対応。
  - 多数の設定プロパティを提供（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 検証など）。
- 対話式設定ウィザードを追加（src/kabusys/config_setup.py）
  - .env の初期作成・更新を支援。シークレット項目はマスクして表示。
  - デフォルト値・選択肢のサポート、保存前の確認プロンプトを実装。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在確認（PyYAML が無ければスキップ）。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や Kill Switch の注意喚起）。
  - --strict オプションで警告を FAIL 扱い可能。
- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ (avg / max / P95) を出力。
  - 日付フィルタ (--from / --to) と DB パス (--db / 環境変数) に対応。
  - 判定基準（閾値）を組み込み、PASS/FAIL 判定を出力。
- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
  - 候補選定・重み算出: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）
  - ポジションサイズ決定（単元丸め、リスクベース / 等配分 / スコア配分、aggregate cap のスケーリング）: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）
  - 上記関数群をパッケージでエクスポート（src/kabusys/portfolio/__init__.py）
- ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
  - 既存ハンドラのクリア、ログレベル・ログディレクトリの解決順を実装。ファイル出力失敗時はコンソールのみで継続。
- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差を吸収して nice / priority を設定。アクセス権限や未対応 OS は警告してスキップ。
  - set_cpu_affinity によりカレントプロセスを最初の N コアに固定可能。
- 研究用ファクター計算モジュール（骨格・モメンタム関数開始）を追加（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受け取り、Momentum 等のファクターを計算する方針・定数を実装。calc_momentum の実装を開始（処理の一部が実装途中）。
- ユーティリティパッケージ初期構成（src/kabusys/utils/__init__.py、tools パッケージの追加）

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / Implementation details
- MONITOR_POLL_INTERVAL: 不正値（0、負値、数値以外）は警告してデフォルト 60 秒にフォールバック。
- PAPER_FILL_MODE: 環境変数で "instant" | "partial" | "never" | "reject" のみ有効。無効値は例外を発生させる。
- .env 自動読み込みはプロジェクトルートが見つからない場合はスキップ（パッケージ配布後の安全策）。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力のみを無効化し、コンソール出力は継続する設計。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームで失敗してもログ警告を出して実行継続する。

Known issues / TODOs
- src/kabusys/portfolio/position_sizing.py:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO。将来的に前日終値や取得原価などのフォールバック価格の導入を検討。
  - lot_size を銘柄別に対応するための拡張（stocks マスタの導入）を検討中。
- src/kabusys/research/factor_research.py:
  - ファイル末尾で calc_momentum 実装が途中で切れている（実装継続が必要）。
- 実運用に際しては BrokerClientFactory / ExecutionEngine / SystemMonitor 等の外部依存（kabuステーション API、Broker 実装など）の実装・設定確認が必要。
- 本リリースは機能実装が中心であり、E2E のテスト・運用監視設定は別途整備を推奨。

参考: 実行例 / CLI
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

署名
- 本 CHANGELOG は提示されたコードベースの内容に基づき記述しました。動作や挙動は実際のランタイム環境・環境変数・外部コンポーネント（DB、ブローカー等）に依存します。
KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/1.0.0/）

[0.1.0] - 2026-04-23
Added
- 初回リリースとして以下の主要コンポーネントを追加。
  - CLI / 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト（実行環境に応じて本番/ペーパー用 DB を分離）。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止する。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、監視用 DB は環境に依らず本番 sqlite_path を使用）。
  - 設定関連
    - config.py: 環境変数読み込み・Settings クラスを追加。プロジェクトルート自動検出による .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。多数の設定プロパティ（DB パス、API トークン、モード判定、監視閾値など）を提供。
    - config_setup.py: 対話式 .env ウィザード。既存値の再利用、シークレット項目のマスキング、.env ファイル生成機能。
    - validate_config.py: 起動前の設定検証ツール（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、--strict モード）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ロギング設定。コンソール(stdout) と 日次ローテーション（TimedRotatingFileHandler）をセットアップ。ログディレクトリ作成失敗時はファイル出力をスキップし安全に動作。
    - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定・CPU affinity ユーティリティ（Windows / POSIX を吸収、権限不足時は警告してスキップ）。
  - ポートフォリオ構築（純粋関数群、DB 参照なし）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）・等金額（calc_equal_weights）/スコア加重（calc_score_weights）重み計算。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score、単元丸め、per-position および aggregate キャップ適用、スケールダウンロジック、cost_buffer サポート）。
    - portfolio/__init__.py: 上記関数をパッケージとしてエクスポート。
  - 研究 / ファクター計算（骨格）
    - research/factor_research.py: DuckDB を用いるファクター計算モジュールの骨格（一連のモメンタム・ボラティリティ等の計算を想定）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL を判定。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - パッケージ情報
    - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- 設定読み込み・パースの堅牢化
  - config._parse_env_line(): export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定等に対応して .env パースの互換性を改善。
- ログ設定の耐障害性
  - logging_setup.setup_logging(): ログディレクトリ作成失敗時もコンソール出力は維持して動作を継続するように改善（FileHandler 作成失敗時のフォールバック）。
- プロセス優先度設定の耐障害性
  - process_priority.set_process_priority/set_cpu_affinity(): 未対応 OS や権限不足時に例外を上げず警告ログを出してスキップする挙動を採用。

Security
- 秘匿情報の扱い
  - config_setup ウィザードでは J-Quants トークンや API パスワードなどのシークレット項目をマスクして表示。.env の Git 管理禁止を README／コメントで明示。

Notes
- 実行環境間の DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番 sqlite_path と完全に分離して動作する。
  - run_monitoring は監視用テーブルに対して環境に無関係に settings.sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
- 停止制御
  - 両起動スクリプトはプロジェクトルート下 data/stop_requested.flag を監視し、存在を検知すると安全に終了/停止する。
  - run_execution は実行中 PID を data/execution.pid に書き込む（Engine 側の pid_file を通じた実装想定）。
- 環境変数自動ロード
  - プロジェクトルートが見つかれば .env を自動で読み込む（OS 環境変数は上書きされない）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- ロギング
  - デフォルトではログは stdout に出力され、さらに logs/<app_name>.log に日次ローテーションで保存（最大 30 日保管）。環境変数 LOG_DIR / LOG_LEVEL で挙動を変更可能。
- Paper Trading 動作
  - PAPER_FILL_MODE（instant/partial/never/reject）の検証を実装。無効な値は例外を投げる。
- CLI
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Breaking Changes
- （初回リリースのため該当なし）

Unreleased
- （次リリースに向けた作業のメモ等はここに記載予定）

---

注: 本 CHANGELOG はソースコードから推測して作成しています。詳細なユーザ向け変更点やリリースノートはリリース作業時に実際のコミット履歴やドキュメントと照合して調整してください。
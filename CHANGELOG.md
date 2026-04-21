Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ の形式に準拠して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-21
-------------------

Added
- 基本パッケージの初回リリース。
- 実行エントリ・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV によるペーパートレード分離（paper_trading 時は専用 MockBroker と専用 SQLite DB を使用）と、停止フラグ / PID 管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）、停止フラグ検知で安全に終了。
- 設定関連
  - config.py: .env 自動読み込み機能（.env, .env.local）を実装。プロジェクトルート検出（.git / pyproject.toml を基準）により CWD 非依存で動作。Settings クラスで各種設定値をカプセル化（KABUSYS_ENV, DB パス, 各 API トークンなど）。
  - config_setup.py: .env を対話式に作成/更新するウィザード CLI を追加。
  - validate_config.py: 起動前に .env や config/*.yaml の不備を検出する検証ツールを追加（--strict オプションで警告を失敗扱いに変更可能）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定・重み算出（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based, equal, score）、単元丸め（lot_size）、aggregate cap によるスケーリング、コストバッファ考慮。
  - portfolio/__init__.py: 上記 API をパッケージエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティ。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定と CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）。
- モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照実装を使用）との連携により、起動時に監視テーブルが存在することを保証（冪等な初期化）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などのレポートを生成。閾値判定で PASS / FAIL を出力。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB を使ったファクター計算の骨格（モメンタム等の計算を意図）。（未完の関数を含むが骨組みを提供）

Changed
- 設計方針
  - 起動スクリプト（monitoring）は KABUSYS_ENV にかかわらず監視用 DB 接続に本番用 sqlite_path を使用する（監視は本番 DB を参照する想定）。
  - run_execution は paper_trading 用 DB を明確に分離（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。
- ロギング
  - ログはデフォルトで stdout に出力するようにして、cron や Task Scheduler など外部のリダイレクト運用に適するようにした。
  - ログファイルは日次にローテートし 30 日分を保持（設定は変更可能）。
- .env の読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で自動ロード。OS 環境変数は protected として .env による上書きを防止。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- エラーハンドリング
  - run_monitoring のポーリングループでは monitor.check_once() が例外を起こしてもループを継続し、例外内容をログ出力して次回ポーリングまで待機する。
  - run_execution は停止フラグ検知で engine.stop() を呼び出して安全終了を図る。
- 環境変数パース
  - config._parse_env_line により、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いに対応。

Fixed
- 環境変数からの MONITOR_POLL_INTERVAL 読み取りを堅牢化
  - 負値や非整数が設定された場合にデフォルト（60 秒）にフォールバックし、警告ログを出力するよう修正（time.sleep に不正値を渡すのを回避）。
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn による通知を行い、起動全体を壊さないように変更。
- process_priority のフォールバック
  - 未対応 OS や権限不足時に例外を握りつぶして警告ログにとどめ、安全に起動を続行するように修正。
- DB 初期化の冪等性
  - init_monitoring_db 呼び出しを起動時に行い、既にテーブルが存在する場合でも安全に続行するように実装（監視テーブルの存在保証）。
- portfolio.calc_score_weights のゼロスコア対応
  - 全銘柄のスコア合計が 0.0 の場合、等金額配分にフォールバックして警告を出すようにした。

Security
- 特になし。

Notes / Migration
- 環境変数 KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでないと ValueError を送出します。既存の設定を移行する際は値を確認してください。
- .env は絶対に Git にコミットしないでください（config_setup にも同旨の注意を記載）。
- run_monitoring は監視用 DB に本番 sqlite_path を使用します。監視データを分離したい場合は設定ファイル側で DB パスを変更してください。
- Paper Trading を行う場合は PAPER_TRADING_SQLITE_PATH（または KABUSYS_ENV=paper_trading と Settings.paper_sqlite_path）を利用して本番 DB と完全に分離してください。

作者
- KabuSys 開発チーム

---
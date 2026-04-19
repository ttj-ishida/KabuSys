CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and aims to maintain
backward compatibility for future releases.

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース。システム全体の主要機能を実装。
  - 実行スクリプト
    - run_execution: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite (data/paper_trading.db) を使用し、本番 DB と分離。スレッドでエンジンを実行し、data/stop_requested.flag による安全停止をサポート。実行時にプロセス優先度を "high" に設定して起動する。 (src/kabusys/run_execution.py)
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。停止フラグ検出でループを終了。 (src/kabusys/run_monitoring.py)
  - 環境設定・検証
    - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI。シークレット入力のマスク、デフォルト表示、保存確認を実装。 (src/kabusys/config_setup.py)
    - validate_config: .env と config/*.yaml の事前検証ツール。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスや YAML パース確認、KABUSYS_ENV=live 時の追加警告、--strict オプションをサポート。 (src/kabusys/validate_config.py)
  - 環境変数設定読み込みと管理
    - config: .env 自動ロード（プロジェクトルートが検出できれば .env を読み込む）、読み込み順 OS 環境 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。複雑な .env パーシング（export 形式、クォート、エスケープ、行内コメントの処理）を実装。各種設定プロパティ（パス、しきい値、PAPER_FILL_MODE 等）と入力バリデーションを提供。 (src/kabusys/config.py)
  - ロギング / プロセスユーティリティ
    - utils.logging_setup: stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。LOG_LEVEL/LOG_DIR の解決順を実装。 (src/kabusys/utils/logging_setup.py)
    - utils.process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）でプロセス優先度（nice / Windows priority class）を抽象化して設定。CPU affinity 設定ユーティリティも提供（pinned cores）。権限不足や未対応 OS の場合は警告を出して安全にスキップ。 (src/kabusys/utils/process_priority.py)
  - ポートフォリオ構築モジュール（純関数群）
    - portfolio.portfolio_builder: シグナル選定（スコア降順、同点タイブレーク）、等重み・スコア加重の重み計算を実装。スコアが全て 0 の場合は等重みへフォールバック。 (src/kabusys/portfolio/portfolio_builder.py)
    - portfolio.risk_adjustment: セクター集中制限の適用（sell 対象を除外、"unknown" セクターは制限しない）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。 (src/kabusys/portfolio/risk_adjustment.py)
    - portfolio.position_sizing: allocation_method (risk_based / equal / score) に基づく株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash に収まるようスケールダウン）と余剰配分ロジック（fractional remainder による追加配分）を実装。コストバッファ考慮もサポート。 (src/kabusys/portfolio/position_sizing.py)
  - Paper Trading 検証ツール
    - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から指標を集計してレポートを出力。稼働率、注文成功率（fill/send）、リスク却下数、平均/最大/P95 レイテンシを計算し、閾値に基づく PASS/FAIL 判定を行う。日付フィルタ (--from / --to) と --db オプションをサポート。 (src/kabusys/tools/paper_verification_report.py)
  - 研究用ファクター計算（着手）
    - research.factor_research: DuckDB 接続を受け取る前提でモメンタム等ファクター計算に着手（calc_momentum 等の設計と定数を実装。関数の途中実装あり）。 (src/kabusys/research/factor_research.py)

Changed
- n/a（初回リリース）

Fixed / Notes
- .env パーサーの強化により複雑なクォートやエスケープ、行内コメントを正しく扱えるようになった（src/kabusys/config.py）。
- ログ設定: ハンドラ二重登録を防ぐため既存ハンドラをクリアしてから設定するようにした（src/kabusys/utils/logging_setup.py）。
- run_monitoring は監視データベース（monitoring）を環境に依存せず本番 sqlite_path を使用する仕様とした（意図的設計）ので、環境混在による誤操作を防止する注意喚起を README 等で行うことを推奨（src/kabusys/run_monitoring.py）。
- run_execution は paper_trading 環境で paper_sqlite_path を使用することで本番データと完全に分離する設計。（src/kabusys/run_execution.py）

Internal
- パッケージメタ
  - __version__ = "0.1.0" を追加。 (src/kabusys/__init__.py)
- ドキュメント参照
  - portfolio や strategy に関する設計注記（PortfolioConstruction.md, StrategyModel.md 参照）が各モジュールに残されており、将来的な参照・拡張を想定。

Security / Backwards compatibility
- 初期公開のため、環境変数に API トークン/パスワードを直書きするモデルを採用（.env を Git に絶対コミットしない注意喚起を config_setup で出力）。運用時は機密管理を推奨。

開発者向けメモ
- config._find_project_root は .git または pyproject.toml を探索してプロジェクトルートを判断するため、配布パッケージ環境下での自動 .env ロードはプロジェクトルートの有無に依存する点に注意。
- process_priority や CPU affinity の設定は権限に依存するため、CI/コンテナ等の環境で実行時に警告が出る可能性あり。

---

今後の予定（例）
- factor_research のファクター計算の完成とユニットテスト追加
- ExecutionEngine / BrokerClient のモックテスト強化
- 設定検証の拡張（YAML スキーマ検証、より詳細な警告/エラー分類）
- ドキュメント（README、運用ガイド）整備

もし CHANGELOG に追記したい修正点やリリース分類（Major/Minor/Patch）などの方針があれば教えてください。
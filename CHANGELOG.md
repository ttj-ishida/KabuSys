# Changelog

すべての重要な変更点を追跡します。フォーマットは「Keep a Changelog」仕様に準拠します。

- 表記: 変更は機能追加 (Added)、変更 (Changed)、修正 (Fixed)、削除 (Removed)、非推奨 (Deprecated)、セキュリティ (Security) に分類しています。
- 日付はリリース日を示します。Unreleased セクションは将来の変更用に残しています。

## [Unreleased]

## [0.1.0] - 2026-04-23

初回リリース。自動売買フレームワーク「KabuSys」の基本機能一式を導入します。主な内容は以下のとおりです。

### Added
- 全体
  - パッケージの初期バージョンを導入。パッケージバージョンは `0.1.0`（src/kabusys/__init__.py）。
- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を高に設定するユーティリティ呼び出しを行い、バックグラウンドスレッドでエンジンを実行。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory でブローカクライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した起動・停止制御を実装。
    - RiskManager に対するデフォルト構成値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入。
  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト: 60秒）。
    - 監視は環境に依らず本番用の sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ (data/stop_requested.flag) による安全停止、例外捕捉で次ポーリングへ継続する堅牢化。
- 設定管理
  - Settings クラスを導入し、環境変数・デフォルト値を統一的に提供（src/kabusys/config.py）。
    - 自動 .env ロード (プロジェクトルートに基づき .env / .env.local を読み込み)。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / KABUSYS_ENV など）。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。PAPER_FILL_MODE の有効値チェックを実装。
- 設定ツール
  - config_setup: 対話式 .env 作成/更新ウィザードを追加（src/kabusys/config_setup.py）。既存値の読み込み、シークレットマスク、保存機能を提供。
  - validate_config: 起動前チェック CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があればパース検証）。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定・kill フラグ設定の警告）。
    - `--strict` オプションで警告を FAIL として扱う。
- ロギング/プロセスユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラと日次ローテーションのファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - LOG_LEVEL / LOG_DIR の環境変数や引数による上書きに対応。
  - プロセス優先度/CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX （Linux/Mac/FreeBSD）を吸収し、安全に設定を試みる（psutil 使用）。権限不足等で失敗しても警告を出しスキップ。
- ポートフォリオ構築モジュール
  - portfolio_builder: 候補選定・重み計算（等分配・スコア加重）を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア加重で全銘柄スコアが 0 の場合は等分配へフォールバックし警告出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター上限超過時に当該セクターの新規候補を除外（unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバック。
  - position_sizing: 発注株数決定ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の各配分方式を実装。
    - 単元株（lot_size）で丸め、portfolio_value・available_cash・max_position_pct・max_utilization 等を考慮した aggregate cap スケーリングを実装。
    - cost_buffer による保守的コスト見積り、スケールダウン時の残差を用いた追加配分ロジックを実装。
- 研究/ツール
  - factor_research: ファクター計算の枠組みを追加（src/kabusys/research/factor_research.py）。モメンタム・移動平均・ATR 等を計算するための定義を含む（関数は部分実装）。
  - tools/paper_verification_report: ペーパートレード検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。閾値（例: 稼働率 >= 99%、P95 <= 200ms）を定義して PASS/FAIL 判定を出力。
    - CLI オプションで期間指定（--from/--to）や DB パス指定（--db）に対応。

### Changed
- なし（初回リリースのため特段の変更履歴なし）

### Fixed
- なし（初回リリース）

### Notes / 実装上の注意点
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、配布後や異なる CWD でも安定して動作するよう設計されています。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- run_monitoring は監視用 DB を環境に関係なく sqlite_path（本番用）で初期化します。監視データとペーパー取引用データを分離したい場合は Settings の設定（PAPER_TRADING_SQLITE_PATH 等）を利用してください。
- process_priority / set_cpu_affinity は権限や OS の差分で失敗する可能性があるため、失敗時は警告を出して処理を継続します。
- position_sizing のスケーリングや price の欠損時の振る舞いについてはコード内に TODO・注意コメントを残しています（将来的な改善点: 銘柄ごとの lot_size 対応、価格フォールバック等）。
- factor_research は設計方針と定数が実装されており、一部機能は引き続き実装が必要（現状はモメンタム計算関数の途中実装を含む）。

---

今後のリリースでは、テストカバレッジ、ドキュメント（PortfolioConstruction.md / StrategyModel.md に記載のアルゴリズム参照）、および factor_research の完全実装やブローカー連携の詳細（エラーリトライ/バックオフ戦略など）を計画しています。必要であればこの CHANGELOG を基に英語版やより細かなリリースノートを作成します。
# CHANGELOG

すべての notable な変更はこのファイルに記録します。書式は「Keep a Changelog」に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 初回リリース
初回公開リリース。日本株向け自動売買フレームワークのコア機能を含みます。

### 追加（Added）
- 基本構成 / バージョン情報
  - パッケージバージョンを `0.1.0` として導入（src/kabusys/__init__.py）。
- 環境設定関連
  - Settings クラス（src/kabusys/config.py）を追加。環境変数から各種設定（DB パス、API トークン、動作環境、ログレベル、監視閾値など）を取得・検証する。
  - 自動 .env 読み込み機能を追加。プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を順に読み込む（OS 環境変数は保護）。
  - .env パーサを実装（引用符付き値、エスケープ、`export` プレフィックス、インラインコメントの取り扱いに対応）。
  - config_setup CLI（src/kabusys/config_setup.py）を追加。対話式ウィザードで .env を生成・更新可能。シークレット項目はマスク表示。
  - validate_config CLI（src/kabusys/validate_config.py）を追加。.env と config/*.yaml の事前検証ツール（--strict オプションで警告をエラー扱い）。
- 実行 / 監視エントリポイント
  - 実行スクリプト run_execution（src/kabusys/run_execution.py）を追加。ExecutionEngine の起動・停止制御、Paper Trading 用の DB 分離、BrokerFactory 経由でブローカクライアントを生成。
  - 監視スクリプト run_monitoring（src/kabusys/run_monitoring.py）を追加。SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。
  - 起動時にプロセス優先度を「high」に設定する仕組みを導入（src/kabusys/utils/process_priority.py）。
  - 停止フラグ（data/stop_requested.flag）および実行 PID（data/execution.pid）による外部制御をサポート。
- ロギング / 運用ユーティリティ
  - 統一的なロギング設定ユーティリティ setup_logging を追加（src/kabusys/utils/logging_setup.py）。stdout 出力 + 日次ローテートされるファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度設定（set_process_priority）、CPU Affinity 設定（set_cpu_affinity）を提供（psutil 利用、Windows/Linux/macOS 対応）。
- ポートフォリオ構築ロジック（純粋関数群）
  - 銘柄選定（select_candidates）、等配分／スコア加重の重み計算（calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - 銘柄ごとの発注株数計算（calc_position_sizes）を実装。リスクベース／等分配／スコア配分の各方式、単元丸め、aggregate cap（利用可能現金に収まるようスケーリング）に対応（src/kabusys/portfolio/position_sizing.py）。
  - ポートフォリオ機能をパッケージレベルでエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 向けツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ（P95 など））を集計し、閾値比較で PASS/FAIL を判定するレポートを出力。
  - P95 計算ユーティリティや日付フィルタ、欠損データへのフォールバック処理を実装。
- 研究用ファクター計算（基盤）
  - factor_research モジュール（src/kabusys/research/factor_research.py）の骨組みを追加。モメンタム、ボラティリティ、流動性、バリュー等の計算方針を記載し、DuckDB 接続を受けて計算する設計を採用（実装は継続中）。

### 変更（Changed）
- 実行と監視で DB の取り扱いを明確化
  - 監視系（run_monitoring）は環境に関係なく本番の sqlite_path を使用するように設計（監視データは分離せず一元化）。
  - 実行系（run_execution）は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB と完全分離（ペーパートレードデータを別 DB に記録）。
- ログ出力のポリシー
  - コンソール出力に stdout を使う（stderr ではなく）。cron/タスクスケジューラからのログの取り回しを考慮。

### 修正（Fixed）
- 環境変数のパース堅牢化
  - .env の quoted value 処理でバックスラッシュエスケープを適切に扱うようにした（内部パーサ実装に反映）。
  - `export KEY=val` 形式のサポートとインラインコメントの取り扱いを追加。
- 起動時の堅牢性向上
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値（非数・0 以下）を検出してデフォルト（60 秒）にフォールバックし、警告ログを出力するようにした。
  - process_priority の設定で権限不足や未対応 OS の場合に例外を吸収して警告ログを出力（起動中断を避ける）。
  - setup_logging でログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップしてコンソールのみで継続するようにフォールバック。
  - Monitoring / Execution の DB 初期化（init_monitoring_db）は冪等に呼べるように設計（既存テーブルがあっても問題にならない）。
- ExecutionEngine の実行制御
  - 起動時に停止フラグが既に存在する場合は起動を行わず安全終了する処理を追加。
  - エンジン実行中に停止フラグを検知したら Engine.stop() を呼んでグレースフルに停止するループを実装。
- Paper verification report の堅牢性
  - DB テーブルが存在しない／カラムがない場合（OperationalError）に各クエリを個別にフォールバックし、レポート生成処理全体が例外で停止しないようにした。
  - P95 計算で空リストを適切に扱う（None 戻り）。

### 注意事項（Notes）
- 構成ファイル（config/*.yaml）は PyYAML が導入されていない環境ではパース検証がスキップされる（validate_config が警告を出す）。
- .env は絶対にリポジトリにコミットしないこと。config_setup による生成時にも注記を出力する。
- PAPER_FILL_MODE の値検証を実施（"instant"|"partial"|"never"|"reject" のみ有効）。無効値は起動時に ValueError を送出する。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに制限される（無効値はエラー）。
- run_monitoring は監視用 DB と DuckDB の両方に接続する。終了処理で両接続を確実にクローズする。

---

今後の予定（例）
- factor_research の各ファクター計算の実装完了と単体テスト整備
- ExecutionEngine・Broker インタフェースの詳細な実装と E2E テスト（ペーパートレード）
- ユニット / 結合テスト追加、CI ワークフロー整備

（この CHANGELOG は現行ソースコードから推測して作成しています。実際のコミット履歴に応じて適宜更新してください。）
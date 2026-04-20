# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルでは、コードベースから推測できる機能追加・変更点・修正点を日本語でまとめています。

今後のリリースでは、ここに差分を追記してください。

## [0.1.0] - 2026-04-20

初回リリース — 基本的な自動売買プラットフォームの骨組みを実装しました。主な内容は以下のとおりです。

### 追加
- 一般
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - 各モジュールにドキュメント文字列（docstring）や使用例を追加。

- 設定管理
  - Settings クラスを実装し、環境変数から各種設定を取得する機能を提供（src/kabusys/config.py）。
  - プロジェクトルート自動検出と .env / .env.local の自動読み込み機能を実装（OS 環境変数を保護して上書き制御）。
  - .env のパースロジックを実装（クォート・エスケープ・インラインコメント対応）。

- 環境設定支援
  - 対話式の環境設定ウィザードを実装（python -m kabusys.config_setup）。.env ファイルの初期作成・更新を支援（src/kabusys/config_setup.py）。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml の基本検証を行う validate_config CLI を実装（python -m kabusys.validate_config）。
  - --strict オプションで警告も失敗として扱うモードを提供。
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を発行。

- ロギング
  - 統一的なログ設定ユーティリティを実装（setup_logging）。コンソール出力（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定（src/kabusys/utils/logging_setup.py）。
  - ログディレクトリ作成失敗時にファイル出力をスキップするフォールバック処理を実装。

- プロセス制御ユーティリティ
  - クロスプラットフォームでのプロセス優先度設定（Windows／POSIX 対応）と CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
  - 実行時に権限不足や未対応 OS の場合は警告を出してスキップする実装。

- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite を使用して本番 DB と分離（data/paper_trading.db、環境変数で上書き可）。
    - BrokerClientFactory を利用したブローカ接続、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを実装。
  - SystemMonitor ポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告後デフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
    - プロセス優先度を起動時に "high" に設定。

- ポートフォリオ構築（純関数群）
  - 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順・タイブレークロジック、スコアが全て 0 の場合のフォールバックを実装。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存ポジションのセクター別エクスポージャー計算、上限超過セクターの候補除外ロジックを実装。
    - レジームに応じた投入資金乗数（bull/neutral/bear）と未知レジームでのフォールバック挙動を実装。
  - 株数決定ロジック（calc_position_sizes）を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金超過時のスケーリング）、
      コストバッファ考慮、残差処理に基づく追加配分を実装。

- リサーチ（計算基盤）
  - ファクター計算の骨組みを追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR / Volume 系ファクター等の算出方針と定数定義を実装（関数 calc_momentum 開始）。（注: ファイル末尾は途中実装の可能性あり）

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を計算。
    - P95 の計算、期間フィルタ（--from / --to）、閾値による PASS/FAIL 判定ロジックを実装（src/kabusys/tools/paper_verification_report.py）。

### 変更
- デフォルトパスの整理
  - DuckDB / SQLite / Paper Trading DB / PID ファイル / ログディレクトリ 等のデフォルトパスを設定し、Settings 経由で取得するよう統一。

- ログの標準出力先
  - コンソール出力を stderr ではなく stdout に統一（タスクスケジューラや cron でのリダイレクトを想定）。

### 修正（安全性・堅牢化）
- .env 読み込みの堅牢化
  - .env の読み込み失敗時に警告を出すようにし、例外で落ちないように変更（保守的なフォールバック）。

- ログファイルハンドラ作成失敗のフォールバック
  - ログディレクトリの作成やファイルハンドラ作成に失敗した場合にコンソール出力のみで継続するよう安全に処理。

- プロセス優先度／CPU affinity のエラー処理強化
  - 権限不足や未対応の OS の場合は警告を出して設定をスキップするように変更。

- 監視・実行ループの停止処理改善
  - stop flag（data/stop_requested.flag）検出によるグレースフルシャットダウンを実装。
  - run_execution のスレッド終了待ちと強制 join のタイムアウトを追加。

### 既知の制約 / TODO（コードから推測）
- factor_research.calc_momentum が途中で終端している可能性があり、ファクター計算の完全実装が今後必要。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価など）は TODO コメントあり。
- 銘柄ごとの lot_size を将来的にサポートするための拡張が検討されている。
- 一部の機能（ExecutionEngine、RiskManager、BrokerClientFactory など）は外部モジュール実装に依存しており、統合テストが必要。

---

今後は、各機能の単体テスト・統合テストの追加、factor_research の完遂、リアルブローカー連携の安全性向上（回復処理・リトライ戦略等）の強化を推奨します。
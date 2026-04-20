# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。Semantic Versioning に準拠することを目指しています。

## [Unreleased]
- 開発中の変更点や小さな修正をここに記載してください。

## [0.1.0] - 2026-04-20
初回リリース。自動売買システム KabuSys のコア機能と運用ユーティリティ群を実装しました。

### Added
- 全体
  - パッケージ初期リリース。モジュール構成を整備（execution, monitoring, portfolio, research, utils, tools 等）。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定・起動関連
  - Settings クラス（kabusys.config）を実装。環境変数・デフォルト値を集中管理。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。`.env`, `.env.local` の読み込み順をサポートし、OS 環境変数を保護する `protected` ロジックを導入。
  - .env 対話式ウィザード CLI（kabusys.config_setup）。既存 .env 読み込み、シークレットマスク、入力支援、ファイル出力を実装。
  - 設定検証 CLI（kabusys.validate_config）。必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、`--strict` モードを提供。

- 実行 / 監視
  - 実行エンジン起動スクリプト（run_execution.py）。環境に応じて paper_trading 用 DB を分離し、Broker クライアントのファクトリで本番／モックを切り替えられる設計。
  - 監視ループ起動スクリプト（run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知で安全にループ終了。
  - PID / stop flag を使ったプロセス制御（data/*.pid, data/stop_requested.flag）。

- データベース / 分析
  - DuckDB 統合（Settings.duckdb_path）。分析用途の DuckDB 接続を受け取る設計。
  - 監視用 SQLite の初期化ユーティリティ（monitoring_db.init_monitoring_db）を呼ぶことで監視テーブルの存在を保証（冪等性）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み計算（portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights）。
  - セクター集中制限・レジーム乗数（risk_adjustment.apply_sector_cap / calc_regime_multiplier）。unknown セクターは制限適用除外。レジームに応じた投下資金乗数を実装（bull/neutral/bear）。
  - 株数決定（position_sizing.calc_position_sizes）。allocation_method（risk_based/equal/score）に対応。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer（手数料・スリッページ推定）を実装。価格欠損時のスキップロジック、端数配分アルゴリズムを実装。

- リサーチ（kabusys.research）
  - ファクター計算フレームワーク（factor_research）のベースを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等を計算する設計（関数を通じて複数ファクターを算出する仕様を用意）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）・リスク却下数を算出し、閾値に基づく PASS/FAIL 判定を出力。日付フィルタ、DB パス指定（環境変数 / --db）に対応し、テーブル欠如時にも安全に動作するフォールバックを実装。

- ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）。stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）。Windows / POSIX の差分を吸収し、優先度（high/normal/low）設定と任意の CPU コア固定を提供。権限不足等のエラーは警告にフォールバック。

### Changed
- 設定ロード / パース
  - .env のパースロジックを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。クォートあり/なし両ケースに対応して安全にパースするように改善。
  - 環境変数の読み込み順を OS 環境 > .env.local > .env として、既存 OS 環境変数を保護する仕組みを導入。

- 実行 / 監視の挙動
  - run_monitoring: Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番 DB パスで一元管理する方針）。
  - run_execution: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と完全に分離する動作を導入。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定するよう変更。

- ロギング
  - StreamHandler は stdout を使用（stderr ではなく）。ログレベル解決順を引数 > 環境変数 > デフォルトに統一。

### Fixed
- 安全性 / 耐障害性
  - .env 読み込みでファイルオープンエラーが発生した場合に警告を出して処理を継続するように修正。
  - ログディレクトリ作成に失敗した場合、ファイルハンドラ作成をスキップしコンソール出力のみで継続する実装により起動失敗の回避を実現。
  - run_execution / run_monitoring で DB 接続を finally ブロックで確実にクローズするようにしてリソースリークを回避。
  - monitoring_db 初期化（init_monitoring_db）を呼び出して監視用テーブルの存在を保証（冪等化）。

### Security
- config_setup の出力ではシークレット項目をマスク表示（対話時と確認時）。
- 環境変数未設定時に Settings の必須プロパティが ValueError を投げることで、起動前に明示的に問題を検知できるようにしています（validate_config にて事前検証推奨）。

### Notes / Known limitations
- 一部の機能（ファクター計算の詳細や ExecutionEngine の内部実装など）は設計に基づくベース実装で、実運用に向けたチューニングや追加のエラーハンドリングが必要です（例: price 欠損時のフォールバック価格、銘柄別 lot_size の将来的対応など）。
- process_priority / cpu_affinity は権限やプラットフォームに依存する処理を含むため、環境によっては設定がスキップされる場合があります（警告ログで通知）。
- Paper Trading の検証レポートは SQLite のスキーマ（trade_logs, system_status, risk_logs 等）に依存します。該当テーブルが存在しない場合は N/A / フォールバック値で出力します。

---

タグ:
- リリース: 0.1.0 (初期機能セット: 実行・監視・設定管理・ポートフォリオ構築・リサーチ基盤・運用ツール・ユーティリティ群)

（必要に応じて各コミットや変更箇所に対応する詳細な項目を追加します。）
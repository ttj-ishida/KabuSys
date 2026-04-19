# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
この CHANGELOG は、与えられたコードベースの内容から機能追加・設計上の特徴・バグ回避などを推測して作成したものです。

## [Unreleased]

### Added
- 監視用の起動スクリプトを追加
  - run_monitoring.py：SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を監視して安全に終了。
- 実行エンジン起動スクリプトを追加
  - run_execution.py：ExecutionEngine をバックグラウンドスレッドで起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用の SQLite（data/paper_trading.db）に完全分離して記録。停止フラグと PID ファイル管理に対応。
- 設定管理と自動読み込み
  - config.py：.env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。quoted/unquoted の .env 行を堅牢にパースし、OS 環境変数を保護する仕組みを実装。複数の設定プロパティ（DB パス、ペーパートレード設定、監視閾値など）を提供。
- 設定ウィザード & 検証 CLI を追加
  - config_setup.py：対話式ウィザードで .env を初期作成・更新。機密項目はマスク表示、保存前に確認プロンプトあり。
  - validate_config.py：.env と config/*.yaml の基本チェックを行う CLI。--strict オプションで警告も失敗扱いにできる。PyYAML がなければ YAML 検証をスキップ。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py：stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py：Windows/Linux/macOS の差を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity 設定関数も提供。権限不足や未対応環境では安全に警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py：候補選定、等金額配分、スコア加重配分を提供。スコアが全てゼロのときは等金額にフォールバック。
  - portfolio/risk_adjustment.py：セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py：リスクベース・等分配・スコア配分に基づく発注株数計算。単元株（lot_size）で丸め、aggregate cap（利用可能現金）を超える際のスケールダウン論理を実装。手数料・スリッページ見積り用の cost_buffer を考慮。
- 分析 / レポートツール
  - tools/paper_verification_report.py：ペーパートレード DB を集計して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を計算し、判定（PASS/FAIL）を出力。デフォルト閾値を定義（例: 稼働率 99% 等）。
- リサーチ用ファクターモジュール（下地）
  - research/factor_research.py：DuckDB を用いたモメンタムや MA200、ATR、出来高指標などファクター計算の骨組みを実装（prices_daily / raw_financials 参照を想定）。設計方針や定数を定義。

### Changed
- データベース設計（起動スクリプトの挙動）
  - 監視コンポーネント（monitoring）は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計。
  - 実行エンジンはペーパートレード環境では専用 SQLite を使用し、本番 DB と完全分離する挙動に。
- 信頼性向上
  - 各種初期化で idempotent な DB 初期化（init_monitoring_db）を呼ぶことでテーブル存在を保証。
  - ポーリングループや ExecutionEngine 実行中の例外はログに残してループ継続や安全停止を行うように実装。

### Fixed
- 環境変数パースの強化
  - .env の quoted 値に対するバックスラッシュエスケープ対応、行内コメントの扱いを改善。export KEY=val の形式にも対応。
- ロギング設定の安全化
  - ログディレクトリ作成失敗やファイルハンドラの作成失敗時に、コンソール出力にフォールバックして起動を継続するように修正。
- プロセス優先度設定の堅牢化
  - 未サポート OS、アクセス権限不足、psutil のプラットフォーム差異に対して例外を握り潰し警告を出して処理を続行するようにした。

### Security
- config_setup.py の出力では機密項目（J-Quants token, KABU API password, LINE token 等）をマスクして表示。
- .env 生成時に「.env を絶対に Git にコミットしないこと」を明示。

---

## [0.1.0] - 2026-04-19

初回リリース。以下の主要機能を含む。

### Added
- 基本アプリケーションパッケージ
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
- 環境・設定管理
  - Settings クラスによる環境変数経由の設定取得（各種パス、閾値、env 判定プロパティを含む）。
  - 自動 .env 読み込み（プロジェクトルート検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 起動スクリプト
  - run_execution.py：ExecutionEngine 起動（BrokerFactory 経由でブローカークライアントを取得、OrderManager / RiskManager / Reconciler 等を組み立て）。
  - run_monitoring.py：SystemMonitor ポーリングループ起動（stop flag を監視）。
- CLI ユーティリティ
  - config_setup.py：対話式 .env 作成ウィザード。
  - validate_config.py：設定検証 CLI（必須環境変数チェック、config/*.yaml の存在・パース検証、KABUSYS_ENV チェックなど）。
- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py：統一ログ設定と日次ローテーション。
  - utils/process_priority.py：クロスプラットフォームのプロセス優先度 & CPU affinity 設定。
- ポートフォリオ構築
  - portfolio モジュール（候補選定、重み計算、セクター制限、レジーム乗数、ポジションサイズ計算）。
- ペーパートレード検証
  - tools/paper_verification_report.py：ペーパートレード結果の集計レポート生成・PASS/FAIL 判定機能を追加。
- リサーチ
  - research/factor_research.py：ファクター計算のための基盤（DuckDB 前提）を追加。

### Changed
- DB の取り扱い
  - ExecutionEngine は paper_trading 環境で別 DB（PAPER_TRADING_SQLITE_PATH）を使用。
  - 監視用 DB は環境に依存せずデフォルトの sqlite_path を使用。

### Fixed
- N/A（初回リリースのため過去のバグ修正履歴なし）

---

注:
- 本 CHANGELOG はコードから推測して作成しています。実際の変更履歴（コミット履歴等）と異なる可能性があります。必要であれば git の履歴やリリースノートに基づいて修正いたします。
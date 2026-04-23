# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
主要なカテゴリ: Added, Changed, Fixed, Removed, Security。

## Unreleased

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
  - 停止制御はリポジトリ直下の data/stop_requested.flag ファイルで行う。
  - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する設計。
  - 監視ループ内で monitor.check_once() の例外を捕捉してログ出力し、ループ継続する耐障害性を確保。

- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を利用し、data/paper_trading.db を専用 DB として使用して本番 DB と分離。
  - 実行エンジンは別スレッドで run_session を起動し、停止フラグ（data/stop_requested.flag）を検知して安全に停止する。
  - 起動時にプロセス優先度を high に設定（set_process_priority を使用）。
  - PID ファイル管理（data/execution.pid）に対応。

- 設定管理（kabusys.config）
  - .env 自動読み込み機構を追加（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env/.env.local の読み込み順と上書きルールを実装（OS 環境変数は protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化するオプションを追加。
  - export プレフィックス対応、クォート文字列（シングル/ダブル）のバックスラッシュエスケープ処理、インラインコメントの取り扱いなど堅牢な .env パーサを実装。
  - Settings クラスで各種設定値をプロパティ化（J-Quants、kabuAPI、LINE、DB パス、監視閾値、環境種別バリデーション等）。
  - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）を追加。

- 設定ウィザード CLI（kabusys.config_setup）を追加
  - 対話式で .env を作成・更新するウィザードを実装。既存値の読み込み・マスク表示・選択肢サポート・保存確認を提供。

- 設定検証 CLI（kabusys.validate_config）を追加
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML を利用したパース検証（PyYAML 未インストール時はスキップ）。
  - KABUSYS_ENV=live 時の追加ガード（LINE 設定チェック、KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションで警告を FAIL 扱いにできる。

- ロギングユーティリティ（kabusys.utils.logging_setup）を追加
  - StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
  - 既存ハンドラをクリアして二重設定を防止。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。

- プロセス優先度・CPU 設定ユーティリティ（kabusys.utils.process_priority）を追加
  - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度を設定。
  - set_cpu_affinity による CPU affinity 設定を実装（存在しない/許可されない場合は警告を出してスキップ）。

- ポートフォリオ構築モジュール（kabusys.portfolio）を追加
  - 銘柄選定: select_candidates（スコア降順＋タイブレーク）、等分配・スコア加重の重み計算 (calc_equal_weights, calc_score_weights)。
  - セクター集中制限: apply_sector_cap（既存保有のセクターエクスポージャを計算し上限超過セクターの候補を除外）。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に基づく乗数、未知レジームはフォールバック）。
  - 株数決定: calc_position_sizes (risk_based / equal / score)、単元株丸め、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を用いた保守的コスト見積りを実装。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）を追加
  - データベース（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率 / 注文成功率 / 送信率 / レイテンシ（avg,max,P95） / リスク却下数）を集計し、閾値に基づいて PASS/FAIL 判定する CLI を実装。
  - --from/--to/--db オプションをサポート。

- research/factor_research（ファクター計算基盤）を追加（モジュール実装の開始）
  - Momentum などのファクター計算を行う設計骨子を含む（calc_momentum の実装着手）。

### Changed
- ログ出力の標準出力を stdout に統一（stderr ではなく）。cron 等でのリダイレクト運用を意識した設計。
- logging_setup が既存ハンドラを一旦 flush/close の上で削除するように変更、複数回呼び出してもハンドラが重複しないようにした。
- DB 初期化 (init_monitoring_db) を呼び出す場所を run_execution/run_monitoring の起動処理に移動し、監視テーブルが存在することを起動時に保証（冪等性を重視）。

### Fixed
- .env パーサのコメント/引用処理を堅牢化し、export プレフィックスやエスケープされたクォートに対応して誤読を防止。
- process_priority の設定が失敗した場合に例外でプロセスを終了させないよう、例外を捕捉してログ警告に変換するよう修正。

### Removed
- なし（現時点で明示的な削除は無し）。

---

## [0.1.0] - 2026-04-23

最初の公開リリース。以下の主要機能を含む初期セット。

### Added
- コア機能
  - 自動売買システムの構成モジュール群（execution / monitoring / portfolio / research / utils / tools）。
  - 実行エンジン（ExecutionEngine）起動スクリプト、監視エージェント起動スクリプト。
  - 設定管理とウィザード（.env の対話式生成、Settings クラス）。
  - 設定検証ツール（validate_config）。
  - ロギング・プロセス制御用ユーティリティ（logging_setup, process_priority）。
  - ポートフォリオ構築・リスク調整・ポジションサイズ算出ロジック。
  - Paper Trading 用の検証レポート生成ツール。
  - パッケージバージョン定義 (__version__ = "0.1.0")。

### Changed
- 初期リリースのため特記事項なし。

### Fixed
- 初期リリースのため特記事項なし。

---

注記:
- CHANGELOG はソースコードの実装内容から推測して作成されています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて調整してください。
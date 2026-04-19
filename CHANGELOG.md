# Changelog

すべての重要な変更履歴をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

重要: この CHANGELOG はコードベース（src/ 以下）から推測して作成しています。実際のリリースノート作成時は差分／コミットログに基づく追記・修正を推奨します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買システム「KabuSys」の基本機能群を追加。

### Added
- 全体
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB と SQLite を組み合わせたデータ保存・解析基盤を採用（duckdb + sqlite）。
- 設定・起動関連
  - Settings クラス（kabusys.config）を追加し、環境変数から設定値を取得する仕組みを提供。
    - 自動 .env 読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 必須環境変数の要求と複数の設定プロパティ（DBパス、KABUSYS_ENV、ログレベル、Paper Trading 関連等）。
  - .env ファイルパーサ（kabusys.config 内）に対応：
    - export KEY=val 形式、引用符つき値（エスケープ処理）や行内コメントの取り扱いに対応。
    - 上書きオプション（override）と保護されたキーセット（protected）をサポート。
  - 対話式環境設定ウィザード（kabusys.config_setup）を追加：
    - .env の初期作成・更新を対話式で支援。シークレット項目はマスク表示。
  - 設定検証ツール（kabusys.validate_config）を追加：
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml 存在と YAML パース検証（PyYAML がある場合）。
    - --strict オプションで警告を失敗扱いにできる。
- 起動スクリプト / 実行基盤
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加：
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（既定: data/paper_trading.db）に記録して本番 DB と分離。
    - プロセス優先度設定（高）と PID ファイル管理、停止フラグ（data/stop_requested.flag）検出による安全停止。
    - 実行エンジンを別スレッドで実行し、停止フラグ検出で安全に停止させるループを実装。
  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）を追加：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告ログを出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知および例外ハンドリングを行い安全に接続をクローズ。
- 監視 / 運用
  - 監視 DB 初期化ユーティリティ（monitoring.monitoring_db の init_monitoring_db 呼び出し）を各起動時に呼び出して監視テーブルの存在を保証（冪等）。
  - PID / stop flag / kill flag 関連の取り扱いを導入（Settings でパスを管理）。
- ロギング・プロセス制御
  - 統一的なログ設定ユーティリティ（kabusys.utils.logging_setup）を追加：
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリの作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加：
    - Windows / POSIX の差分吸収。優先度（high/normal/low）設定と CPU affinity 固定機能を実装。
    - 権限不足など失敗時は警告を出してスキップする安全設計。
- ポートフォリオ構築 / 発注支援
  - portfolio モジュールを追加（純粋関数群、DB 非依存、メモリ内計算）：
    - portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights を実装（スコア降順、同点のタイブレーク等）。
    - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた資金乗数）を実装。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分、lot 単位丸め、aggregate cap スケーリング、cost_buffer を考慮）を実装。多数の安全弁とログ出力を含む。
- ツール / レポート
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加：
    - システム稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）、DB パスの引数/環境変数サポートを提供。
    - P95 計算、NULL 気味のデータやテーブル未存在時のフォールバックを適切に扱う。
- 研究・ファクター計算
  - research モジュール（kabusys.research.factor_research）でモメンタム等のファクター計算基盤を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - モメンタム、MA200 乖離、ATR、流動性指標などの計算方針を実装（calc_momentum 等、営業日ベースのウィンドウ設計）。
    - （注: calc_momentum 関数実装が途中で切れているため追加実装が必要。）
- その他
  - モジュール間の依存注入設計：BrokerFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等の組立てが run_execution で行われる。
  - RiskManager の初期設定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をデフォルトで設定。

### Changed
- （初期リリースのため過去変更なし）

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 や文字列等）を検出し、デフォルトにフォールバックして警告ログを出すように実装。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ生成で例外が上がらないよう保護し、コンソールのみで継続する挙動を保証。

### Removed
- （初期リリースのためなし）

### Security
- .env は絶対に Git にコミットしないことを README / config_setup のコメントで強調。
- validate_config で本番（KABUSYS_ENV=live）時の LINE 通知設定不備や Kill Switch の誤設定を警告するガードを追加。

### Notes / Known issues
- research.factor_research.calc_momentum の実装がファイル末尾で途中になっており、続きの実装が必要（現状は設計コメントまで含まれる）。
- apply_sector_cap の価格欠損時の扱い（price が 0.0 の場合）に TODO コメントがあり、将来的に前日終値や取得原価でのフォールバックが望まれる。
- position_sizing は現状で全銘柄共通の lot_size を想定しており、将来的に個別 lot_size 対応に拡張予定の TODO がある。
- 本番運用時は KABUSYS_ENV=live に設定する前に validate_config で全項目を入念に確認してください（特に LINE 通知設定、KILL_FLAG_CLEAR_ON_START）。

---

（この CHANGELOG はコードの静的解析・読解に基づくサマリです。実際のコミット履歴と差異がある場合は、該当コミットや PR の説明を優先してください。）
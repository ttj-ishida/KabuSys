# Changelog

すべての注目すべき変更を記録します。これは Keep a Changelog の慣習に従っています。  
注: 以下の変更点は与えられたコードベースの内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 初回リリース
初期リリース。自動売買システム KabuSys のコア機能群を実装しました（設定管理、起動スクリプト、ログ基盤、監視・実行コンポーネント、ポートフォリオ構築、ユーティリティ、検証ツールなど）。

### Added
- 設定・起動関連
  - Settings クラス（src/kabusys/config.py）
    - 環境変数に基づく設定取得 API を提供（J-Quants, kabuステーション, DBパス, ログ設定等）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（無効な値は例外）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE をサポート。
  - 自動 .env ロード機構
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み。
    - OS 環境変数を保護する protected オプションを採用。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env を作成／更新するウィザードを提供。
    - J-Quants トークンや KABU API パスワード等の必須項目を扱う UI を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML がある場合はパース検証）を実施。
    - --strict フラグで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB から完全分離（BrokerClientFactory により MockBrokerClient を利用）。
    - PID ファイル、停止フラグ（data/stop_requested.flag）検出による安全な起動・停止制御。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の起動とポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視用 DB は本番 DB を参照する想定）。
    - 停止フラグの検出でループを終了。例外発生時はログ出力して次ポーリングへ継続。

- ロギング・プロセス制御
  - 統一ロギングセットアップユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収した set_process_priority（high/normal/low）を提供。
    - set_cpu_affinity によるプロセスのコア固定機能を実装（指定なしは変更しない）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター別上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバック。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じて株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）を実装。
    - cost_buffer による手数料・スリッページ見積りをサポート。残差処理で lot 単位の追加配分を行う。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を抽出してレポートを作成。
    - デフォルトの閾値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）による PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）と --db オプションを提供。

- データリサーチ（調査用）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム等のファクター計算設計（DuckDB を用いた prices_daily / raw_financials ベースの計算）。関数群の骨格と定数を実装（モメンタム期間・ATR・ボリューム等）。
    - （注）ファイル末尾で計算開始直前で切れている箇所があり、以降の実装は継続予定。

- パッケージ初期化
  - パッケージメタ情報（src/kabusys/__init__.py）に __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため "Changed" は該当なし。将来のアップデートで追記予定）

### Fixed
- （初回リリースのため "Fixed" は該当なし。実装段階での安全策や入力検証を多数含む）

### Notes / 運用上の注意
- .env の自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml）。配布後の動作を想定して __file__ を起点に探索しますが、ルートが見つからない場合は自動ロードをスキップします。
- run_monitoring は監視用プロセスとして常に本番用 sqlite_path を参照します（監視対象は本番 DB＝監視は環境に依存しない想定）。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を分離して使用します。ペーパートレードでは MockBrokerClient を使用して発注をシミュレーションします（BrokerClientFactory 経由）。
- 停止/強制停止制御はプロジェクトルートの data/stop_requested.flag や kill.flag、PID ファイルを用いて行います。KILL_FLAG_CLEAR_ON_START による自動クリア設定は本番での誤設定に注意してください（validate_config で警告あり）。
- logging_setup はデフォルトで stdout に出力するため、cron 等での起動時に stdout/stderr の扱いを一元化できます。ログファイル出力は logs/ 配下に日次ローテーションで保存（作成失敗時はコンソールのみ）。

---

将来的には以下のような拡張・改善が想定されます：
- research モジュールの完全実装（ファクター計算の SQL / 正規化処理）
- ExecutionEngine / SystemMonitor の内部実装詳細（現状は起動フロー・依存組立を確認）
- 個別銘柄単位の lot_size をマスタに持たせる等の細かな設計拡張
- モニタリング・アラートの外部通知（LINE 連携の本格実装）

もし特定の変更点を詳細に反映してほしい場合（例: リリース日付、コミットハッシュ、実際のバグ修正履歴など）、その情報を提供してください。
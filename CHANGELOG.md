# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般的な注記
- この変更履歴は、与えられたソースコードを基に機能追加・実装方針を推測して作成しています。実際のコミット履歴ではありません。
- バージョンはパッケージの __version__（0.1.0）を基に初回リリースとして記載しています。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期実装
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止処理はプロジェクト内の `data/stop_requested.flag` ファイルで制御。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用の SQLite（デフォルト `data/paper_trading.db`）を使用し、Mock Broker を通じて発注を行う想定（BrokerClientFactory を利用）。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine をバックグラウンドスレッドで実行し、`data/stop_requested.flag` による停止制御と `data/execution.pid` 管理を実装。
    - RiskManager, OrderManager, Reconciler 等の依存コンポーネントを組み立てる初期設定（既定のリスク設定値を使用）。

- 設定管理
  - kabusys.config
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、.env 自動読み込みを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env パース機能を実装（export プレフィックス、シングル/ダブルクォート対応、エスケープ、インラインコメント処理）。
    - Settings クラスを実装し、環境変数の取得・検証（必須項目の要求、列挙値チェック、パスの Path 型化、paper_fill_mode の検証等）を提供。
    - DB パス、PID/kill flag、CPU/Memory/Disk 閾値など運用用設定をプロパティで提供。
    - ユーティリティ的なフラグ（is_live / is_paper / is_dev）を追加。

  - kabusys.config_setup
    - .env の対話式ウィザードを追加。既存 .env 読み込み、項目ごとの説明、シークレットマスク、デフォルト提示、保存前確認を実装。
    - 書き出しテンプレートを定義し、.env に安全に書き込む機能を提供（「.env は絶対に Git にコミットしない」旨のヘッダを出力）。

  - kabusys.validate_config
    - 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合はスキップ）を行う。
    - `--strict` オプションにより警告を失敗扱いにできる。
    - 本番（live）向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定の危険性等）を実装。

- 監視・モニタリング関連
  - monitoring_db 初期化呼び出し（init_monitoring_db）を各起動スクリプトから行い、監視テーブル存在を保証。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux / macOS / FreeBSD）の差分を吸収してプロセス優先度を設定するユーティリティを追加（psutil 使用）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（利用可能コア数より多い指定では全コア使用へフォールバック）。
    - 権限不足や未対応 OS に対するフォールバックおよび警告処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。score が全て 0 の場合のフォールバックを実装。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）：既存保有のセクター別エクスポージャー計算に基づき新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）：市場レジームに応じた投下資金乗数を返す（bull/neutral/bear）。
    - 未知レジームや unknown セクターに対するフォールバックと警告を実装。
  - portfolio.position_sizing
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した調整を実装。
    - risk_based 方式ではリスク許容率（risk_pct）と stop_loss_pct を用いたベース株数計算を実装。
    - aggregate スケールダウン時に残差の大きさ順で lot 単位の追加配分を行うロジックを実装。

- 研究用 / データ処理
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加。モメンタム、ボラティリティ、流動性等のファクター算出ロジック（prices_daily テーブル参照）を実装。
    - 移動平均・ATR 等の窓関数を SQL で実装し、データ不足時の None ハンドリングを考慮。

- ツール
  - tools.paper_verification_report
    - ペーパートレードの検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB パス指定（--db / 環境変数）をサポート。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する閾値を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。
    - データ欠損に対する N/A 表示と堅牢なエラーハンドリングを実装。

- パッケージエクスポート
  - kabusys.portfolio パッケージで主要関数群を __all__ により公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

補足・既知の注意点
- apply_sector_cap にて price が欠損（0.0）の場合にエクスポージャーが過小見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する予定。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別単元のサポートを想定する TODO コメントあり。
- process_priority や CPU affinity は権限や OS に依存するため、設定に失敗した場合は警告ログを出してスキップする安全設計。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では自動読込がスキップされる場合がある（その場合は環境変数を直接設定すること）。

今後の予定（推奨）
- 単体テストと E2E テストの追加（特にポジションサイズ算出、スケーリングロジック、DB 初期化系）。
- config/*.yaml のスキーマ検証を強化（PyYAML が無い環境では警告となるため依存関係を明示）。
- lot_size の銘柄別対応、price フォールバックロジックの実装、より詳細なモニタリング指標（メトリクス出力）の追加。
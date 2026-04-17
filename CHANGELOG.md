# Change Log

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

履歴は逆順（新しいリリースが上）で記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回リリース — KabuSys のコア機能・CLI・ユーティリティを追加。

### 追加 (Added)
- パッケージ全体
  - 初期バージョンの公開。パッケージメタ情報は `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を組み合わせたデータ処理基盤を採用（設定でパス指定可能）。
- 設定・環境変数管理
  - `.env` 自動ロード機能を実装（プロジェクトルートに基づき `.env` / `.env.local` を読み込む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - 独自の .env パーサを実装。`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - `Settings` クラスを導入し、J-Quants / kabu API / LINE / DB /監視閾値 / 環境種別 などの設定をプロパティとして提供。
  - 環境判定ヘルパ（is_live / is_paper / is_dev）を提供。
  - ペーパートレード専用設定:
    - PAPER_FILL_MODE（instant/partial/never/reject）検証を実装。
    - PAPER_TRADING_SQLITE_PATH で paper_trading 用 SQLite を分離可能。
- CLI / スクリプト
  - 環境設定ウィザード: `kabusys.config_setup`  
    - 対話式で `.env` を作成/更新。必須項目・デフォルト・シークレット表示等をサポート。
    - `.env` を書き出す際に注意書きを付与（Git にコミットしない旨）。
  - 設定検証 CLI: `kabusys.validate_config`  
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス親ディレクトリの存在チェック、`config/*.yaml` の存在および（PyYAMLがあれば）パース検証、`live` 環境向けの追加ガード（LINE通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
  - 実行エンジン起動スクリプト: `kabusys.run_execution`
    - BrokerClientFactory によるブローカークライアント生成。
    - `paper_trading` 環境では MockBroker を用い、SQLite を本番と分離（デフォルト: data/paper_trading.db）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、スレッドで実行。停止フラグ検知で安全停止。
    - プロセス優先度を起動時に "high" に設定（可能な場合）。
  - 監視ループ起動スクリプト: `kabusys.run_monitoring`
    - SystemMonitor を使用したポーリング監視ループを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 監視用 DB 初期化（本番 sqlite_path を使用して監視テーブルを保証）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
- モニタリング
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出してテーブル存在を保証（冪等）。
- ポートフォリオ構築（pure functions）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank によるタイブレークでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: 既存保有に基づくセクター集中制限を適用し、上限を超えるセクターの新規候補を除外。sell_codes を除外して評価可能。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じて投下資金乗数を返す（デフォルト値・フォールバック含む）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。lot_size（単元）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング、残差の再配分ロジックを実装。価格欠損時のスキップや安全弁を導入。
- リスク管理 / 実行ロジック（雛形）
  - RiskManager / RiskConfig（デフォルト値）を用意し、初期ポートフォリオ価値を broker.get_available_cash() から取得して設定。
  - ExecutionEngine の起動・停止処理（pid ファイル経由の管理、停止フラグハンドリング）をサポート。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`:
    - set_process_priority(level): Windows（priority class）および POSIX（nice 値）に対応。権限不足や未対応 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へ CPU affinity を設定（実行環境の利用可能コア数を考慮）。権限不足時は警告してスキップ。
- 解析 / 研究用モジュール
  - `kabusys.research.factor_research`:
    - DuckDB を用いたファクター計算（モメンタム: 1M/3M/6M、MA200 乖離、ボラティリティ: ATR20、流動性指標等）。営業日ベース・ウィンドウ幅・欠損時の None 扱いなどの設計方針を採用。
- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定する閾値を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）。
    - DB の日付フィルタ、P95 計算（サンプル数が 0 の場合のハンドリング）等を実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- .env の読み込み失敗時に警告を出して処理を継続するよう堅牢化（ファイルアクセス例外ハンドリング）。
- 監視ループ内の check_once() 例外を捕捉してログ出力し、ループ継続する安全化処理を追加。

### 注意事項 (Notes)
- 本リリースでは監視（run_monitoring）は常に本番用の `sqlite_path` を使用する設計です（環境にかかわらず監視 DB を共通化）。
- Paper Trading は発注処理を本番 DB と完全に分離する設計（デフォルト DB: data/paper_trading.db）。環境変数と config wizard を利用してパスを調整してください。
- `.env` ファイルは機密情報を含むため Git にコミットしないでください（config_setup に警告ヘッダを付与）。
- OS 権限の制約により process priority / cpu affinity の設定に失敗する場合があります。その場合は警告ログが出力され、処理は継続します。

### 既知の制限 / 今後の改善案
- position_sizing の lot_size は現在全銘柄共通で固定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap のエクスポージャー計算で価格データが欠損する場合に過小評価される可能性があり、前日終値等のフォールバックを検討中。
- factor_research のファクター計算は prices_daily / raw_financials に依存するため、データ品質・欠損に対する追加堅牢化が必要。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の開発履歴やコミットメッセージとは差異があり得ます。）
# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-18

初回リリース。本リポジトリに含まれる主要機能・ツール群を追加。

### 追加 (Added)
- コア設定/環境管理
  - Settings クラスによる環境変数ラップ（J-Quants、kabuステーション、DBパス、監視閾値など）。
  - 自動 .env ロード（プロジェクトルートの .env → .env.local、OS 環境変数を保護して上書き制御）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env のパース強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。

- 設定支援ツール
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）：.env の作成・更新をサポート。シークレット項目はマスク表示。
  - 設定検証 CLI（python -m kabusys.validate_config）：必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML 利用時）等をチェック。--strict モードをサポート。

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine を起動するためのエントリーポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して本番/モックのブローカークライアントを生成。
    - RiskManager/RiskConfig のデフォルト設定を用意（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
    - 実行時に execution.pid を生成・管理し、data/stop_requested.flag による安全な停止処理に対応。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず Settings.sqlite_path（監視用 sqlite）を使用して DB 初期化（init_monitoring_db）を保証。
    - 停止フラグ検出、例外キャッチでループ継続、KeyboardInterrupt による終了処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - risk_adjustment: セクター集中上限適用 (apply_sector_cap)、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear を実装、未定義レジームは警告して 1.0 にフォールバック）。
  - position_sizing: ポジションサイズ算出 (calc_position_sizes)。allocation_method に "risk_based" / "equal" / "score" をサポート。lot_size（単元株）で丸め、コストバッファを考慮した aggregate cap スケーリングと残差配分ロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB 接続を利用したモメンタム・ボラティリティ・流動性ファクター計算（mom_1m/3m/6m、ma200 偏差、ATR20、20日平均売買代金等）。データ不足時の None ハンドリングあり。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を提供。Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、失敗時は警告を出力してスキップ。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定するしきい値を定義（デフォルト: uptime 99%、fill_rate 90%、send_rate 95%、P95 200 ms）。

- DB/分析
  - DuckDB と SQLite の両方を想定した接続管理（各モジュールで受け取り、分析用と監視用で分離）。

- パッケージ化情報
  - パッケージバージョンを __version__ = "0.1.0" に設定。

### 変更 (Changed)
- .env 読み込みポリシー
  - OS 環境変数を保護するため、デフォルトでは OS 環境変数が優先され、.env ファイルは未設定キーのみで上書き。.env.local は .env を上書き可能だが OS 環境は常に保護される。

### 修正 / 安定化 (Fixed)
- 環境変数パースの堅牢化
  - クォート付き値のバックスラッシュエスケープ処理、インラインコメントの扱い、export プレフィックス対応を追加して .env パースの誤動作を低減。
- ポーリング間隔のバリデーション
  - MONITOR_POLL_INTERVAL に 0 以下や非整数が設定された場合に警告してデフォルト値へフォールバック。

### 注意事項 (Notes)
- 監視プロセスは「環境にかかわらず」Settings.sqlite_path を使用して監視 DB を初期化・接続します。本番/ペーパートレードの分離は run_execution 側で PAPER_TRADING_SQLITE_PATH を使用する設計です。運用時は監視 DB と実行用 DB のパス設定に注意してください。
- .env は機密情報を含むため、README 等にもある通り Git へコミットしないでください（config_setup にも同旨の警告を出力）。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。実行環境にこれらがない場合は該当機能が限定されます（例: PyYAML がないと config/*.yaml の検証はスキップされ、psutil がないとプロセス優先度/affinity の設定で警告が出ます）。

### 既知の制約 / TODO
- position_sizing の価格欠損時のフォールバック（price が 0.0 の場合の過少見積り）について注釈を残しており、将来的に前日終値や取得原価などのフォールバック価格導入を想定。
- lot_size は現状グローバル共通の想定。将来的には銘柄毎の単元情報を取り込む設計を検討。

---

今後のリリースでは、ExecutionEngine / EngineConfig / Reconciler 等の詳細実装に関する統合テスト、監視アラート通知（LINE 連携）の実装強化、duckdb ベースの追加分析クエリ群の拡充を予定しています。
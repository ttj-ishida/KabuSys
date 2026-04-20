# Changelog

すべての非互換変更や重要な追加・修正はここに記録します。
フォーマットは「Keep a Changelog」準拠、セマンティックバージョニングに従います。

次回リリースのための未リリース項目はありません — 最初の公開版を下に記載します。

## [0.1.0] - 2026-04-20

初回公開リリース。

### 追加 (Added)
- 基本アプリケーションパッケージを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数 / 設定読み込み機能を追加（kabusys.config）。
  - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境 > .env.local > .env。
  - 自動読み込みを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメント等に対応。

- 設定オブジェクトを提供（kabusys.config.Settings）。
  - 主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須、未設定時は例外）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（instant/partial/never/reject の検証）
    - PID/kill フラグ関連パス
    - CPU/MEM/DISK 閾値
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL 検証

- 対話式環境設定ウィザードを追加（kabusys.config_setup）。
  - .env の初期生成・更新を支援する CLI ツール。
  - シークレット項目のマスク、選択肢表示、既存値の再利用機能を備える。
  - 保存時に .env を所定フォーマットで書き出す（Git へコミットしない旨の注意文つき）。

- 設定検証 CLI を追加（kabusys.validate_config）。
  - .env と config/*.yaml（存在すれば）を起動前に検査。
  - 必須環境変数のチェック、KABUSYS_ENV の妥当性検査、ログレベル、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がある場合）。
  - KABUSYS_ENV=live の場合の本番向けガード（LINE 通知設定や Kill Flag 挙動の警告）。
  - --strict オプションで警告を FAIL 扱いにできる。

- 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
  - ExecutionEngine の起動ロジック（プロセス優先度設定、DB 接続、Broker クライアント生成、OrderManager/RiskManager/Reconciler 組み立て、スレッド実行と停止フラグ処理）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了。
  - エンジンの PID を data/execution.pid に記録する想定（pid_file 経由）。

- 監視（SystemMonitor）起動スクリプトを追加（kabusys.run_monitoring）。
  - ポーリングループを実装。デフォルト間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは production monitoring DB に集約）。
  - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
  - check_once() 実行時の例外はログに残して次回ポーリングへフォールバック。

- ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
  - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
  - ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > デフォルト "logs/"。
  - 既存ハンドラをクリアして二重設定を防止。
  - ファイル出力に失敗してもコンソール出力は継続。

- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows/Linux/macOS の差分を吸収して優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定する機能を提供。
  - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - 銘柄選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 配分重み: calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数: apply_sector_cap（既存保有からセクター暴露を算出、上限超過セクターの候補除外）、calc_regime_multiplier（bull/neutral/bear マップとフォールバック）。
  - 株数算出: calc_position_sizes（risk_based / equal / score の割当方式、単元株（lot）丸め、aggregate cap スケーリング、cost_buffer 考慮）。

- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading SQLite DB（デフォルト: data/paper_trading.db）から各種指標を算出してコンソールに出力。
  - 指標:
    - システム稼働率（system_status）
    - 注文成功率 / 送信率（trade_logs）
    - リスク却下数（risk_logs）
    - レイテンシ（平均・最大・P95）
  - Pass/Fail 基準を定義:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) に対応。

- DuckDB / SQLite の併用を導入。
  - DuckDB: 分析用（prices_daily 等）・パフォーマンス重視の列志向 DB（デフォルト path: data/kabusys.duckdb）。
  - SQLite: 監視・トレード履歴等の軽量永続化（デフォルト path: data/monitoring.db、ペーパートレード時は data/paper_trading.db）。

- monitoring_db 初期化呼び出しを追加（init_monitoring_db を監視・実行の起動時に呼ぶ） — テーブル存在の保証（冪等）。

- research/factor_research モジュール（骨格）を追加。
  - モメンタム / ボラティリティ / 流動性 / バリュー等のファクター算出を想定した設計と定数を導入。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針。
  - （注）ファイルは一部実装途中（末尾で切れている部分あり）。

### 変更 (Changed)
- ログ出力は標準出力として stdout を利用するよう統一（cron / スケジューラでの取り扱いを意識）。
- 環境変数の .env パースロジックを強化（export プレフィックス対応、クォート・エスケープ・インラインコメントの扱い）。

### 修正 (Fixed)
- ExecutionEngine / Monitoring の起動時に監視テーブルが存在しない場合に備え、init_monitoring_db を呼び出して初期化するようにした（冪等処理）。

### セキュリティ (Security)
- .env 書き出しテンプレートに「.env を絶対に Git にコミットしないこと」を注記（config_setup の出力）。

### ドキュメント（コードコメント等）
- 各モジュールに使用方法・設計意図・注意点をコードドキュメントとして追加（例: PortfolioConstruction.md / StrategyModel.md 参照の旨や TODO コメント）。
- validate_config と config_setup に利用方法の記載。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター算出 SQL/ロジックの完成）。
- ExecutionEngine / Monitoring の各コンポーネント（broker, order_manager, risk_manager 等）のユニットテスト追加。
- 単体テスト・CI の設定、およびパッケージ配布手順の整備。

もし特定ファイルの変更点をより詳細に分解して履歴化したい場合は、その旨を教えてください。ファイル単位での差分推定にも対応します。
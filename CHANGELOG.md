# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-17

初期リリース — KabuSys のコア機能をまとめて導入します。主に設定管理、実行／監視の起動スクリプト、ポートフォリオ構築ロジック、検証ツール、研究用ファクター計算、ユーティリティを含みます。

### Added
- 設定・環境管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。OS 環境変数を保護する仕組みを持つ。
  - 高度な .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
  - Settings クラスを提供し、アプリケーション設定（J-Quants / kabu API トークン・パスワード、DB パス、Paper Trading 用設定、監視閾値、環境種別など）をプロパティ経由で取得可能に。

- 起動スクリプト / 実行・監視
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB から完全分離。
    - BrokerClientFactory により実環境／モックのブローカークライアントを切替。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで実行。PID ファイル、停止フラグ（data/stop_requested.flag）対応。
    - RiskManager にデフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（monitoring の永続化先を固定）。
    - 停止フラグ / KeyboardInterrupt による安全な終了処理、sqlite / duckdb のクローズ処理を実装。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等に実行可能）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重によるウェイト算出。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター露出に基づき新規候補を除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0、未知時に警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定を実装。単元株（lot_size）丸め、ポジション上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、余剰キャッシュによるロット配分の再割当ロジックを実装。

- 研究／分析
  - research.factor_research:
    - DuckDB 接続を用いてモメンタム／ボラティリティ系ファクターを計算（mom_1m/mom_3m/mom_6m, MA200 偏差, ATR20, 平均出来高等）。DuckDB SQL とウィンドウ関数を利用。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下件数、平均/最大/P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - CLI オプション --from / --to / --db をサポート。デフォルト DB は data/paper_trading.db。
    - Pass/Fail 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- 開発支援 CLI
  - config_setup.py:
    - 対話式の .env 作成・更新ウィザードを追加。シークレットマスク、デフォルト表示、オプションのスキップ、確認後保存を提供。保存テンプレートにはコメントとセクションを付与（.env を Git にコミットしないよう明記）。
  - validate_config.py:
    - 起動前の設定検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）構文検証、KABUSYS_ENV=live 時の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を実装。--strict で警告を失敗扱いにできる。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority と set_cpu_affinity を追加。Windows / POSIX（Linux, macOS, FreeBSD）を吸収し、権限不足や未対応環境では警告を出して安全にスキップ。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- config_setup で生成される .env に対して「絶対に Git にコミットしない」旨を明記。
- Settings._require により必須の機密情報（J-Quants / kabu API）未設定時は起動前に ValueError を発生させて明示的に失敗する挙動を採用。

### Notes / Behavior highlights
- run_monitoring の監視 DB は KABUSYS_ENV に依らず sqlite_path（デフォルト: data/monitoring.db）を使用するよう設計されています。監視データの保存先を環境で分離したい場合は設定を変更してください。
- run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離されます。
- MONITOR_POLL_INTERVAL に不正値（0、負値、非整数）を設定するとログに警告を出しデフォルト間隔（60 秒）を使用します。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかであることを検証し、無効値は例外を投げます。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム非対応時に例外を投げず警告でスキップするため、デプロイ先の権限に依存しません。

---

今後の予定（例）
- ExecutionEngine / BrokerClient の詳細実装の追加・安定化。
- strategy / data モジュールの拡充（シグナル生成、バックテスト機能など）。
- config/*.yaml の詳細なスキーマ検証およびサンプル生成スクリプトの強化。
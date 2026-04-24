# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

ルール: 変更は[Added], [Changed], [Fixed], [Deprecated], [Removed], [Security] のいずれかのカテゴリで整理します。

最新: Unreleased — 今後の改善予定や既知の制限を記載しています。

---

## [Unreleased]

### Added
- ドキュメントや将来の改善候補を CHANGELOG に追加（本セクションは開発中の機能や改善案を示します）。

### Known limitations / To do
- research/factor_research.py が途中で切れており、モメンタム等のファクター計算関数の実装・完成が必要。
- position_sizing の将来的拡張点として銘柄別単元（lot_size）のマスタ対応がコメントで残されている。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価など）未実装。
- 単体テストやエンドツーエンドテストのカバー状況の明記はないため、テスト追加が推奨される。

---

## [0.1.0] - 2026-04-24

初回リリース。以下の主要コンポーネントと CLI / ツール群を導入。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - `kabusys.config.Settings` クラスを導入。環境変数経由で各種設定（J-Quants、kabu API、DBパス、監視しきい値、実行環境判定等）を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。優先順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パースの堅牢化（シングル/ダブルクォート・エスケープ・コメント処理・export プレフィックス対応）。

- 環境設定ウィザード
  - `kabusys.config_setup` に対話式ウィザードを実装（`.env` の初期作成・更新支援）。
  - プロンプト表示、既存値の読み込み、シークレット値のマスク表示、保存確認など。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML があれば）、本番環境向けの追加ガードを提供。
  - `--strict` オプションにより警告を FAIL 扱いにできる。

- 実行用スクリプト・エンジン
  - `kabusys.run_execution` を追加。起動時にプロセス優先度を "high" に設定し、ExecutionEngine を起動するためのブートストラップを実装。
  - Paper Trading と本番の DB 分離: `KABUSYS_ENV=paper_trading` の場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計（BrokerClientFactory の使用を前提）。
  - ExecutionEngine の依存コンポーネント組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、duckdb 接続など）を組み込み。
  - エンジンの PID 管理（data/execution.pid）、停止フラグ（data/stop_requested.flag）による安全停止処理を実装。

- 監視用スクリプト
  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループを起動。
  - 環境変数 `MONITOR_POLL_INTERVAL` からポーリング間隔を指定可能（デフォルト 60 秒）。不正値（0 以下や非数）は警告を出してデフォルトにフォールバック。
  - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（監視用 DB は本番データを参照）。

- 監視 DB 初期化
  - `init_monitoring_db` を呼び出し、監視用テーブルの存在を保証（冪等）。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
  - LOG_LEVEL / LOG_DIR の解決順を実装し、既存ハンドラの二重登録防止処理を行う。
  - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続するフェイルセーフを実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority` を実装。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、psutil を用いて nice / priority を設定。アクセス権限不足等は警告ログでスキップ。
  - `set_cpu_affinity` を実装。最初の N コアにプロセスを固定する機能（引数 None で無効）。入力妥当性チェックあり。

- ポートフォリオ構築（Portfolio）
  - `kabusys.portfolio.portfolio_builder`:
    - `select_candidates`: BUY シグナルをスコア降順で選別（同点は signal_rank でタイブレ）。
    - `calc_equal_weights`: 等金額配分。
    - `calc_score_weights`: スコア加重配分。スコア合計が 0 の場合は等金額配分にフォールバック（警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`: セクター集中制限を適用し、既存保有が上限を超えるセクターの新規候補を除外。unknown セクターは制限対象外。
    - `calc_regime_multiplier`: 市場レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`: allocation_method ("risk_based", "equal", "score") に基づき発注株数を算出。単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（available_cash）を考慮したスケールダウンロジックを実装。cost_buffer を用いた保守的コスト見積りをサポート。
  - `kabusys.portfolio.__init__` で主要関数をエクスポート。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH）を読み、以下の指標を計算・出力:
    - system_status テーブルから稼働率（uptime_pct）、エラー数
    - trade_logs から注文作成/成立/送信数、注文成功率・送信率
    - risk_logs からリスク却下数
    - trade_logs の latency_ms を用いた平均・最大・P95 レイテンシ
  - デフォルトの合格基準（しきい値）を定義:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - コマンドライン引数で期間指定（--from/--to）と DB パス（--db）をサポート。存在しない DB は明示的にエラーメッセージを出力。

- Research / ファクター計算（骨格）
  - `kabusys.research.factor_research` にファクター計算モジュールの骨格を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum/Value/Volatility/Liquidity を計算する設計方針を実装。いくつかの定数と calc_momentum の開始部分が含まれる（実装未完）。

- パッケージ構成
  - パッケージのエクスポート（__all__）で主要サブパッケージを定義。

### Changed
- （初回リリースにつき履歴上の変更はなし）

### Fixed
- （初回リリースにつき履歴上の修正はなし）

### Notes / Behavior details
- 監視（run_monitoring）は環境にかかわらず monitoring DB として Settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計。Paper Trading と本番の分離は Execution 側で実施。
- stop フラグの位置: プロジェクト data ディレクトリ内の `stop_requested.flag` を用いて安全に停止できる設計。Execution は起動時に既にフラグが立っていると起動を中止する。
- PID ファイル管理: ExecutionEngine 起動時に data/execution.pid を用いてプロセスを識別する想定。
- ログ出力は標準出力（stdout）を基本とし、可能であれば日次ローテートされたログファイルにも出力される。

---

今後の予定（例）
- factor_research の完全実装（モメンタム/ATR/売買代金・出来高指標・財務指標の取り込みと正規化）。
- 銘柄別の lot_size マスタ対応（position_sizing の拡張）。
- 価格欠損時のフォールバックロジック追加（apply_sector_cap の精度向上）。
- 監視・実行周りの E2E テスト追加と、より詳細なメトリクス収集。

---

（注）本 CHANGELOG は提示されたソースコードからの推測に基づき作成されています。実際のコミット履歴やリリースノートとは差異がある場合があります。必要であれば、実際のコミットログやリリース日を元に更新いたします。
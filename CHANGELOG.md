# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成した変更履歴です。

## [Unreleased]

- なし（今後の変更点をここに記載）

## [0.1.0] - 初回リリース
最初の公開バージョン。システムのコア機能・CLI・ユーティリティ群を実装。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境変数管理
  - Settings クラスを実装し、環境変数経由でアプリ設定を提供（J-Quants / kabu API / DB パス / モード等）。
  - .env ファイルの自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルート（.git または pyproject.toml）から探索するため CWD に依存しない。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化サポート。
  - .env パーサーを強化: export プレフィックス対応、クォート文字のエスケープ対応、インラインコメント処理などをサポートする堅牢なパーシング実装を追加。
  - 環境変数アクセス時の検証（存在チェックや有効値チェック）を行う `_require` と各種プロパティを提供（例: `paper_fill_mode` の値検証、`env` の有効値検査など）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の初期作成・更新を支援。
  - シークレット項目のマスク表示、選択肢サポート、既存 .env の読み込み・再利用機能を提供。
  - `.env` のテンプレート書き込み機能 `_write_env` を実装。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ユーティリティを実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML があれば内容検証、なければ警告）を実施。
  - `--strict` フラグで警告を失敗（exit code 1）扱いにするオプションを追加。

- 実行エントリポイント
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を設定して DB に接続、ブローカー生成、各コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててスレッドでセッションを実行する。停止フラグ（data/stop_requested.flag）と PID ファイルの管理をサポート。
    - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、本番 DB とは分離した `data/paper_trading.db` を使用（データ分離）。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期利用可能現金はブローカーから取得して初期値として使用。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。

- モニタリング DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出して監視用テーブルが存在することを保証（冪等）。

- ユーティリティ
  - `utils.process_priority` を実装。Windows と POSIX（Linux/macOS 等）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを提供。また CPU affinity を設定する `set_cpu_affinity` を追加。権限がない場合に警告を出して安全にスキップする実装。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`：候補選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights。全スコアが 0 の場合は等金額にフォールバック）を追加。
  - `portfolio.risk_adjustment`：セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（regime: bull/neutral/bear のマッピング。未知値は警告とともに 1.0 へフォールバック）。
  - `portfolio.position_sizing`：各銘柄の発注株数計算を実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、1 銘柄上限、aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング配分ロジックを提供。

- リサーチ / ファクター計算
  - `research.factor_research`：DuckDB を用いて価格・財務データ（prices_daily / raw_financials）からファクターを計算する関数を実装（モメンタム: mom_1m/3m/6m、MA200乖離; ボラティリティ: ATR, avg_turnover 等）。計算は SQL + Python を組合せて実行。データ不足時は None を返す設計。

- 紙トレード検証ツール
  - `tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。期間指定可能（--from / --to）、PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（しきい値: 稼働率 >=99%、成功率 >=90% 等）を出力。P95 計算や欠損データ（テーブルがない等）の取り扱いを考慮。

### Changed
- プロセス起動時の共通振る舞い
  - run_execution/run_monitoring 起動時にプロセス優先度を最初に "high" に設定するように統一。

- .env 読み込みの挙動明確化
  - OS 環境変数は保護され、.env の上書きは .env.local のみが許可される（既存 OS 環境変数は保護）。
  - プロジェクトルートが特定できない場合、自動ロードをスキップする安全設計。

### Fixed
- .env パースの安定化
  - クォート内のバックスラッシュエスケープや export プレフィックス、コメントの扱いなど、従来の単純実装で陥りがちだった誤解析を改善。

### Notes / Important behaviour
- 監視（run_monitoring）は KABUSYS_ENV の値に関わらずデフォルトの production 用 sqlite_path（Settings.sqlite_path）を使う実装になっているため、環境変数を変更しても監視 DB の切り替えが行われない点に注意（paper_trading は run_execution 側で分離）。運用時は意図した DB パスと権限を確認してください。
- Paper Trading 実行時は ExecutionEngine が paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番のモニタリング DB / データと完全分離される設計になっているため、テスト・検証データが混入しないよう配慮済み。
- process_priority の設定は OS と実行権限に依存するため、権限不足や未対応 OS では警告を出してスキップする安全策が取られている。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時にはリリース日やコミットハッシュ、より詳細な変更点（API のシグネチャ変更、パラメータ追加/削除、既知の制約や移行手順など）を追記してください。
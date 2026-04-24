# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-24

初回公開リリース。

### 追加 (Added)
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動と停止フラグ検出処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - エンジンの PID を data/execution.pid に出力（設定に依存）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 停止制御はプロジェクトルートの data/stop_requested.flag によるフラグ方式を採用。
    - 監視は KABUSYS_ENV にかかわらず監視用（本番）SQLite（settings.sqlite_path）を使用して初期化・接続。
    - DuckDB 接続（settings.duckdb_path）を併用。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境関連
  - config.py: 環境変数 / .env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env/.env.local の自動読み込み（OS 環境変数を保護）。
    - .env の行パーサは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - Settings: 各種プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / KABUSYS_ENV 検証 等）を提供。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の取得ユーティリティを実装。
  - config_setup.py: 対話式の .env 作成ウィザードを追加。
    - シークレット入力のマスク表示、既存 .env 読み込み、選択肢やデフォルト提示、保存機能。
    - 書き出しテンプレート（コメント付き）を生成。

- 検証ツール
  - validate_config.py: 起動前に .env および config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告も FAIL 扱いにできる。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py: 一貫したロギング設定ユーティリティを追加。
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル / ログディレクトリ解決の優先順を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度／CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応。設定失敗時は警告を出してスキップ。
    - set_cpu_affinity によるコア固定機能を提供。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio/portfolio_builder.py:
    - 銘柄候補の選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定の銘柄を除外可能、"unknown" セクターは上限適用外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - lot_size（単元）丸め、1銘柄上限・aggregate cap・cost_buffer（手数料・スリッページ想定）を考慮したスケーリング処理、残余配分ロジックを実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を抽出して判定（PASS/FAIL）。
    - P95 計算、CLI 引数 --from / --to / --db をサポート。
  - tools/__init__.py を追加（パッケージ化）。

- 研究 / ファクター計算
  - research/factor_research.py: DuckDB を使用したファクター計算用モジュールの雛形を追加（モメンタム、MA200、ATR、出来高系など算出予定）。（実装途中）

- パッケージ情報
  - kabusys.__init__: バージョンを 0.1.0 に設定。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意 / 重要な挙動
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視用の本番向け SQLite）を使用して監視テーブルを初期化します。監視データを分離したい場合は Settings.sqlite_path を適切に設定してください。
- run_execution は paper_trading 環境では paper_sqlite_path を使用して本番データベースとは分離されます（デフォルト: data/paper_trading.db）。
- .env の自動読み込みはプロジェクトルートが特定できる場合に行われ、OS 環境変数は保護されます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）はデフォルト (60 秒) にフォールバックし、警告を出力します。

---

今後の予定（例）
- research/factor_research の完全実装とテスト
- ExecutionEngine / SystemMonitor 周りの統合テスト強化
- 単体テスト・CI の追加（現在は主に手動テスト想定）
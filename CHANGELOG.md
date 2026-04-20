# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: リポジトリ内のソースコードから推測して記載しています。実際の変更履歴と差異がある場合は適宜調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

### Added
- 基本パッケージ導入
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。アプリ起動時にプロセス優先度を設定し、SQLite / DuckDB に接続して ExecutionEngine をデーモンスレッドで実行する。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler といった依存コンポーネントの組合せを行う。
    - data/stop_requested.flag による外部停止フラグ検出、PID ファイル保存（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視用 DB は常に production path）。
    - stop フラグ検出でループを終了、check_once() の例外を捕捉して次ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml により検出）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を優先、.env.local は上書き可能だが OS 環境は保護）。
    - 複数の設定プロパティを持つ Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の入力検証（"instant"|"partial"|"never"|"reject" のみを許可）。
    - KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを含む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。

- 設定ユーティリティ（CLI）
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する機能を追加。シークレット項目はマスク表示、既存値の読み取りと Enter での再利用に対応。
    - 出力時に .env を書き出すテンプレートを用意（.env はコミット禁止の注意文付与）。
  - validate_config.py
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ検証、YAML ファイルの存在と簡易パース（PyYAML がない場合はスキップ）を実施。
    - KABUSYS_ENV=live の場合に注意喚起（LINE 通知設定や Kill Switch の設定等）。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレークロジック）、等配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（既存ポジションからセクター別エクスポージャ計算、上限超過セクターの候補除外）。
    - レジーム乗数 calc_regime_multiplier（"bull","neutral","bear" をマッピング、未知のレジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 各種 allocation_method をサポート（"risk_based","equal","score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer 考慮、残差分配ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。
    - 既存ハンドラのクリア処理、多重設定の回避、ログディレクトリ作成のフォールバック処理を実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定関数を追加（Windows/Linux/Mac を考慮、psutil を使用）。CPU affinity 設定関数も提供。

- モニタリング関連
  - monitoring_monitoring_db の初期化呼び出しを run_execution/run_monitoring で実施し、監視テーブルが存在することを保証（冪等）。

- DuckDB / 分析連携
  - 起動スクリプトで DuckDB 接続を確立するようにし、研究・分析モジュールが使用可能（duckdb_path を Settings で管理）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力する。
    - デフォルト DB パスは data/paper_trading.db。--db, --from, --to オプションで絞り込み可能。
    - デフォルトの合格基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）を定義。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - Momentum 等のファクター計算用モジュールを追加（DuckDB を利用、複数期間のリターン・MA200乖離・ATR 等の計算方針を実装予定）。（ファイル末尾は途中実装の痕跡あり）

### Changed
- （初版のため該当なし）

### Fixed
- .env パーサーの強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース、インラインコメント処理ルールを導入。
  - 無効行（空行・コメント）の無視、key が空の行のスキップなど堅牢化。
- .env ロードの安全性
  - .env.local を上書きモードで読み込む際に OS 環境変数を保護（protected set）することで意図しない上書きを防止。
- ログ設定の堅牢化
  - 既存ハンドラを flush/close のうえ削除してから再設定することで多重ハンドラ登録・重複ログ出力を防止。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続する。

### Removed
- （初版のため該当なし）

### Security
- .env は生成時に「絶対に Git にコミットしないこと」と明示。対話ウィザードはシークレット項目をマスク表示。

### Notes / Known limitations
- run_monitoring は「監視用 DB に関して環境設定を無視して常に本番 sqlite_path を使用する」設計になっている（意図的）。運用時は sqlite_path の値に注意。
- apply_sector_cap 内で price_map に欠損（0.0）がある場合にエクスポージャが過少推定され、ブロック判定が甘くなる旨の TODO コメントあり（将来的にフォールバック価格の導入を検討）。
- research/factor_research.py はファイル末尾で途中実装（start_da...）が見られるため、完全実装が必要。
- process_priority / cpu_affinity の設定は OS 権限に依存し、権限不足時には警告を出してスキップする挙動。
- validate_config における YAML パースは PyYAML の存在に依存。PyYAML 未インストール時は YAML 内容チェックをスキップするが警告を出す。

---

この CHANGELOG はソースの状態から推測して作成しています。実際のコミット履歴やリリースノートと合わせる場合は差分を反映してください。必要であれば各項目をより細かく（該当ソースファイル・関数名・実装上の注意点など）展開できます。どの程度の詳細が必要か指示ください。
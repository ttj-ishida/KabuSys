# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載します。  
初回リリース（v0.1.0）はリポジトリ内の主要機能を実装した内容をまとめたものです。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys の基盤機能（設定管理、実行エンジン、監視、ポートフォリオ構築、ユーティリティ、CLI ツール等）を実装しました。

### 追加した機能
- コアランタイム
  - run_execution.py: ExecutionEngine 起動スクリプト（プロセス優先度設定、停止フラグ対応、デーモンスレッドで実行）。
    - KABUSYS_ENV=paper_trading 時は専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper_trading 時はモッククライアントを利用する想定）。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は一貫して本番対象を確認する設計）。
    - 停止フラグファイルを検知して安全にループ終了、例外はログ出力して次のポーリングへ継続。

- 設定管理
  - config.py: Settings クラスを導入し、環境変数（.env/.env.local の自動ロードを含む）から一元的に設定を取得。
    - .env 自動ロード: プロジェクトルート（.git または pyproject.toml を探索）を検出して .env/.env.local を読み込む（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメントの扱い等に対応。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE の検証、有効な KABUSYS_ENV/LOG_LEVEL 判定、閾値設定など）を提供。
  - config_setup.py: ユーザー対話式の .env 作成/更新ウィザードを追加。

- 設定検証
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在（および PyYAML があればパース検証）等を実施。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30 日保持）を設定。ログディレクトリ・ログレベルは引数/環境変数で制御。
    - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力にフォールバックして安全に動作。
  - utils/process_priority.py:
    - set_process_priority(level) で Windows/Linux（およびサポート POSIX）を抽象化して優先度を設定。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity 固定をサポート（権限・プラットフォームにより失敗しても警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソート・上位選定。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中度上限チェック（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバック（警告を出力）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め、per-stock 上限、aggregate cap によるスケールダウン処理を実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的なコスト算出、残差を考慮して lot 単位で再配分するロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計しレポートを生成。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどの指標集計と PASS/FAIL 判定（閾値をファイル先頭に定義）。
    - P95 計算と日付フィルタ、DB が存在しない/テーブルがない場合のフォールバック処理を実装。

- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB 経由でのファクター計算（Momentum/Value/Volatility/Liquidity）設計を導入。モメンタム計算関数の骨格を実装（実装途中のファイルあり）。

### 変更（設計上の重要な決定）
- .env の自動ロード順序を明確化:
  - OS 環境変数 > .env.local（上書き） > .env（未設定時にセット）
  - OS 環境変数は保護され、.env.* で上書きされない。
- 監視 (monitoring) の DB は環境に依らず本番 sqlite_path を使用する設計とした（監視対象は一貫して本番）。
- run_execution は paper_trading 時に paper 用 DB を使用して本番 DB と完全分離するよう実装。
- ログ出力は stdout を基本にしつつ、ファイルハンドラは日次ローテーションで保存（失敗時は stdout にフォールバック）することで、cron/タスクスケジューラ環境での取り回しを容易にした。

### 修正（堅牢性向上 / フォールバック）
- .env パーサ:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
- Settings の各種プロパティで不正値検出時に明示的な例外や警告を出すようにした（例: PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証）。
- process_priority / set_cpu_affinity は権限不足・未対応 OS の場合に例外を出さず警告でスキップするようにした（実稼働環境での安全化）。
- calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックして警告を出す。
- calc_position_sizes:
  - 価格欠損時のスキップ、単元株丸め、aggregate cap によるスケールダウン、残余キャッシュでの端数配分ロジックを実装して過剰発注を防止。
- logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗した場合、コンソール出力のみで継続する堅牢な挙動に。

### 既知の制約・今後の改善予定（TODO / 注意点）
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされ、除外判定が緩くなる可能性がある。将来的には前日終値等のフォールバック価格を導入予定。
- position_sizing の lot_size は現在グローバルな単一値（デフォルト 100）を利用。将来的に銘柄毎の lot を持つ拡張を検討（stocks マスタの導入等）。
- research/factor_research.py は実装途中の箇所があり、完全なファクター計算ロジックは今後追加予定。
- run_monitoring/run_execution はファイルフラグ（data/stop_requested.flag 等）を用いる運用設計。コンテナ運用やプロセス管理ツールとの連携要件に応じて改良の余地あり。

### その他
- パッケージバージョンを初期設定: __version__ = "0.1.0"
- ドキュメントやコメントに設計思想（PortfolioConstruction.md / StrategyModel.md 等を参照する旨）を残しています。

---

将来的なリリースでは、Strategy 実装、バックテストパイプライン、各種データ取得・ETL、監視のアラート送信（LINE 統合）、および研究モジュールの完成を予定しています。必要であれば、この CHANGELOG を更に詳細化して Git のコミット単位やモジュール別差分を追記します。どの粒度で残したいか指示をください。
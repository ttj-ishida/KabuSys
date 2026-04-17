# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
タグ付けやリリースは semver に従います。

なお、本 CHANGELOG は現在のコードベースの内容から推測して作成したもので、実際のコミット履歴とは対応しない可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション初期実装を追加。
  - パッケージ情報:
    - kabusys.__version__ = "0.1.0"
- 設定管理:
  - .env ファイル自動ロード機能を実装（プロジェクトルートに .git または pyproject.toml がある場合に読み込む）。
  - 高度な .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの考慮）。
  - 環境変数の読み込み順序: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - Settings クラスを提供し、アプリケーション設定（API トークン、DB パス、環境モード、各種閾値など）をプロパティで取得。
  - Settings で値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 環境設定ウィザード CLI:
  - `kabusys.config_setup`（python -m kabusys.config_setup）により対話式で .env を生成・更新する機能を追加。
  - シークレット項目は表示をマスク、保存前に確認プロンプトを表示。
  - 生成される .env には注意書きを含め、Git にコミットしないよう促す。
- 設定検証 CLI:
  - `kabusys.validate_config`（python -m kabusys.validate_config）で環境変数や config/*.yaml の存在・簡易検証を実行可能に。
  - --strict オプションで警告を FAIL 扱いにできる。
  - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML が有れば YAML のパース検証、本番環境用の追加ガードを実装。
- 実行系 / 監視系起動スクリプト:
  - run_execution: ExecutionEngine を起動する CLI を追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、BrokerClientFactory により MockBrokerClient を利用。
    - Engine をデーモン Thread で起動し、data/stop_requested.flag による外部停止検知を実装。PID ファイル管理を含む。
    - Execution 関連コンポーネントの組み立てを行う: OrderRepository、OrderManager、RiskManager（デフォルト設定を含む）、Reconciler、ExecutionEngine。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値の時はデフォルトにフォールバックし警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行い、SystemMonitor.check_once() を定期実行。data/stop_requested.flag による停止検出を実装。
    - 監視は環境設定に関わらず本番 sqlite_path を使用する設計（監視 DB は本番 DB を参照する想定）。
- モニタリング DB 初期化の呼び出し（init_monitoring_db）。
- プロセス優先度 / CPU affinity ユーティリティ:
  - utils.process_priority.set_process_priority(level) を実装（Windows と POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を実装（指定が None の場合は変更しない）。
  - 権限不足や未対応 API の場合は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) を追加。
  - portfolio.risk_adjustment: セクター集中制限適用(apply_sector_cap)、レジームに応じた乗数(calc_regime_multiplier) を追加。
  - portfolio.position_sizing: 発注株数計算(calc_position_sizes) を追加。risk_based / equal / score の allocation_method、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮を実装。
  - portfolio パッケージの __all__ を整備。
- リサーチ / ファクター計算:
  - research.factor_research: DuckDB を使ったモメンタム/ボラティリティ等のファクター計算関数（calc_momentum, calc_volatility など）を実装。データは prices_daily / raw_financials テーブルを前提。
- ツール:
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し、閾値に基づき PASS/FAIL を判定。
    - デフォルト閾値を定義（uptime 99%、fill_rate 90%、send_rate 95%、p95_latency 200ms）。
    - 日付レンジフィルタ対応と DB 存在チェック。
- ロギング/メッセージ:
  - 多くの処理経路で適切な INFO / WARNING / DEBUG / EXCEPTION ログ出力を追加。

Changed
- 設計上の挙動:
  - 監視（run_monitoring）は環境にかかわらず monitoring 用 DB 接続に settings.sqlite_path（本番用パス）を使用する設計に決定。
  - .env ローダーは OS 環境変数を保護し、.env.local は .env より優先して上書きする（ただし OS 環境は保護される）。

Fixed
- .env のパースに関する堅牢性向上:
  - クォート内のエスケープ処理、export プレフィックス、インラインコメントの適切な扱いを実装して不正パースの回避。
- process_priority のプラットフォーム差分に起因する import 時エラーを防止するため getattr を用いたフォールバック実装を追加。

Security
- config_setup においてシークレット項目は表示をマスクしてユーザーに入力を促すようにし、.env ファイルは Git へコミットしない旨のコメントを追加（警告表示）。
- Settings._require により必須環境変数が未設定の場合は明示的にエラーとすることで起動時に秘密情報の未設定を検出。

Notes / Implementation details
- 多くのモジュールは外部依存（psutil, duckdb, sqlite3, PyYAML）を前提としている。PyYAML がインストールされていない場合、validate_config は YAML 内容検証をスキップする。
- ExecutionEngine / BrokerClientFactory / SystemMonitor 等の内部実装（発注ロジック・DB スキーマなど）は本 CHANGELOG の説明対象外だが、起動/停止フローおよび依存コンポーネントの組み立てが含まれている。
- calc_position_sizes 等の資金配分ロジックは単元株（lot_size）丸め・cost_buffer を考慮しており、aggregate cap 超過時に再スケーリングと余剰分の分配処理を行う。

今後の予定（例）
- 単体テスト・E2E テストの整備
- ストラテジー生成部分と ExecutionEngine の結合テスト
- 銘柄別 lot_size 情報を持つマスタの導入と position_sizing の拡張
- 監視系の DB スキーマ・メトリクス拡張とアラート機能の追加

---

（注）この CHANGELOG は現状のソースコードから推測してまとめたものであり、実際のコミットメッセージや開発履歴と完全に一致するものではありません。必要があれば、各機能ごとにより詳細な変更履歴をコミット単位で再構築できます。
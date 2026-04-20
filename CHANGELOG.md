CHANGELOG
=========

フォーマットは Keep a Changelog に準拠しています。
※ バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリースとしてシステム全体の主要コンポーネントを追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、MockBrokerClient を用いる設計をサポート。起動時にプロセス優先度を "high" に設定、停止フラグ / PID 管理を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔上書き可能。監視用 DB は本番 sqlite_path を使用（環境に依存せず）。
  - 設定関連
    - config.py: 環境変数 / .env ロード機能を追加。プロジェクトルート検出（.git または pyproject.toml）、.env/.env.local の読み込み順や OS 環境変数の保護を実装。各種設定プロパティ（DB パス、PAPER_FILL_MODE、閾値、環境判定など）を提供。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。秘密項目のマスク表示や保存プレビュー機能を備える。
    - validate_config.py: .env および config/*.yaml の事前検証ツールを追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML が無ければ YAML 検証をスキップする旨を警告。
  - ポートフォリオ構築モジュール（純粋関数群、DB非依存）
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等分配・スコア加重の重み計算を実装（スコア全0 の場合は等分配へフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有を考慮して候補除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - portfolio/position_sizing.py: 株数決定ロジックを実装。risk_based / equal / score の配分方式、単元（lot_size）による丸め、合計投下額が利用可能現金を超える場合のスケーリング／残余配分を実装。コストバッファ等のパラメータを受け取る。
    - portfolio/__init__.py: 上記関数群をエクスポート。
  - utils
    - utils/logging_setup.py: stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を用いた統一ログ設定ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する。
    - utils/process_priority.py: プラットフォーム抽象化されたプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX(Linux/Mac/FreeBSD) に対応し、許可エラーや未対応 OS は警告でスキップする。
  - monitoring
    - run_monitoring.py（上記）と monitoring 側初期化呼び出し（init_monitoring_db の呼び出し）は監視テーブルの冪等な初期化を保証。
  - execution サイドの補助
    - run_execution.py 内で BrokerClientFactory の利用、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを網羅（初期化パターンを提供）。
  - tools
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。期間フィルタ（--from/--to）・DB パス指定（--db / 環境変数）に対応。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出し、事前定義の閾値と比較して PASS/FAIL を出力。DB テーブルが存在しない場合でも sqlite3.OperationalError を捕捉して graceful に振る舞う。
  - research
    - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）の実装を開始。DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計（関数 calc_momentum ほか、定数や方針を定義）。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- ログ挙動と運用面の仕様を明記・統一。
  - logging_setup: stdout を利用することで Task Scheduler や cron 等での出力リダイレクト運用を想定。
  - .env 自動読み込み: OS 環境変数を保護しつつ .env/.env.local を適切な優先度で読み込むように実装。

Fixed
- 環境変数パーサの堅牢化（config._parse_env_line）
  - export プレフィックスのサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの適切な無視などに対応。
- run_monitoring.py / run_execution.py における停止フラグ検出・受動的終了ロジックを実装し、安全に停止できるようにした。
- process_priority のエラー条件でアクセス拒否や未実装 API を捕捉することで起動失敗を回避。

Security
- .env の生成テンプレート（config_setup）に注意書きを追加: ".env は絶対に Git にコミットしないこと" を明記。

Notes / Implementation details
- MONITOR_POLL_INTERVAL: run_monitoring で環境変数からポーリング間隔を取得。1未満や非整数の場合は警告を出してデフォルト（60 秒）にフォールバック。
- PAPER_TRADING の分離: run_execution は settings.is_paper を参照して paper_sqlite_path（デフォルト data/paper_trading.db）を使用。ペーパートレードの DB は本番 DB と完全分離される想定。
- RiskManager の初期設定は Execution 側で指定（例: max_position_pct=0.20, max_utilization=0.80 など）。初期値として broker.get_available_cash() を参照する箇所があるため、BrokerClient 実装は get_available_cash() を提供する必要あり。
- position_sizing のスケーリングは lot_size 単位で端数処理を行い、残余キャッシュを用いて fractional 残差の大きい順に追加配分するロジックを実装。
- apply_sector_cap: "unknown" セクターの銘柄は上限制約の対象外（除外しない）という方針。
- calc_regime_multiplier: 未知のレジームはログ警告の上 1.0 にフォールバック。
- paper_verification_report: デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、期間フィルタは ISO8601 UTC 形式に変換して DB クエリに適用。

Acknowledgements / Known limitations
- research/factor_research.py は大枠の実装（calc_momentum 等）を定義していますが、ファイルが一部で切れているため未完の関数や追加検証が残る可能性があります。
- position_sizing や sector cap の計算は価格データが欠けている場合のフォールバック（例: 前日終値など）を TODO コメントで示しており、将来的な拡張を予定しています。
- YAML 検証は PyYAML の有無に依存。PyYAML が無い環境では YAML 内容検証をスキップし警告を出します。
- process_priority / cpu_affinity はプラットフォーム・権限に依存するため、環境によっては効果が限定的。

--------------------------------------------------------------------------------
今後のリリース案（提案）
- research モジュールの完全実装（ファクター計算の詳細と統合テスト追加）
- ExecutionEngine / Broker クライアントのユニットテスト拡充（モックを用いた挙動検証）
- position_sizing の銘柄別 lot_size 対応（マスタ導入）
- monitoring の SystemMonitor 実装詳細公開とアラート連携（LINE 通知など）
- ドキュメント: API 仕様・運用手順書の整備（起動手順、.env 管理、監視/復旧手順）
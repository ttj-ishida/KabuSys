# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-18
初回リリース。自動売買システム KabuSys のコア機能と運用ユーティリティを含みます。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) による安全な終了処理を実装。
- 設定管理・初期化
  - config.py: 環境変数読み込みと Settings クラスを実装。  
    - .env / .env.local 自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。  
    - 複数の設定プロパティ（DB パス、API トークン、Paper Trading の挙動、しきい値など）を提供。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）などのバリデーション実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - 初期 .env 作成・既存 .env の更新を支援。機密値はマスク表示。
- 設定検証
  - validate_config.py: 起動前の環境検証 CLI を追加。  
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在確認（PyYAML があればパース検証）を行う。  
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - コンソール出力（stdout）と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL を尊重。
    - 既存ハンドラのクリア処理やディレクトリ作成失敗へのフォールバックを実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティ。  
    - Windows / POSIX (Linux, macOS 等) を吸収して set_process_priority を提供。psutil を利用し失敗時は警告でスキップ。  
    - set_cpu_affinity によるコア固定機能を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限およびレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数決定・リスクベース配分・単元株丸め（calc_position_sizes）。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。aggregate cap の際のスケーリングと残差処理（lot 単位での再配分）を実装。
  - portfolio/__init__.py: 上記 API をパッケージ公開。
- 研究用ファクター計算
  - research/factor_research.py: DuckDB を使ったモメンタム/ボラティリティ等のファクター計算の骨組みを追加（prices_daily / raw_financials を前提）。（一部実装が続く設計）
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。  
    - 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出し PASS/FAIL 評価を行う。  
    - コマンドライン: python -m kabusys.tools.paper_verification_report （--from/--to/--db オプション対応）。
- DB 初期化
  - 各起動処理で監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す処理を追加（冪等に実行）。
- パッケージメタデータ
  - __init__.py にてバージョンを 0.1.0 に設定。

### Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron/タスクスケジューラでの取り回しを考慮）。
- .env ローダーの挙動を明確化
  - export KEY=val 形式に対応。
  - クォート付き値のエスケープ解釈、インラインコメント処理の詳細な取り扱いを実装。
  - _load_env_file に protected パラメータを導入し OS 環境変数の上書きを防止。
- データベースパスの分離方針
  - 実行エンジンは Paper Trading モード時に専用 SQLite を使用して本番データと隔離する設計へ（設定可能: PAPER_TRADING_SQLITE_PATH）。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を用いる旨を明示（監視データの一元化）。

### Fixed / Robustness
- run_monitoring.py のポーリング間隔取得で無効値を検出した際にデフォルトにフォールバックする処理を追加して time.sleep の ValueError を回避。
- process_priority / set_cpu_affinity で権限不足や未対応プラットフォーム時に例外を握り潰してワーニングで継続するように変更（実行継続性向上）。
- config_setup の .env 読み書きで既存ファイルの読み取り・上書きを安全に行う実装を追加。
- paper_verification_report の各クエリを sqlite3.OperationalError で保護し、対象テーブルが存在しない場合でも Graceful に動作するようにした。

### Security
- .env ファイル生成時に「絶対に Git にコミットしないこと」という注意を明記。
- シークレット値はウィザード表示時にマスク表示。

### Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの骨格を実装しているが、一部実装が続いている（ファイル末尾で未完の場所あり）。今後データ取得と完全な計算ロジックの追加が必要。
- position_sizing / apply_sector_cap の価格欠損時のフォールバックは現状限定的（TODO コメントあり）。前日終値や取得原価の利用など拡張を検討。
- config/*.yaml のパース検証は PyYAML がインストールされている場合のみ行われる。

---

以上がコードベースから推測して作成した変更履歴です。必要であれば、各項目をさらに分割・詳細化したり、リリース日やバージョン番号を調整したりできます。どのように整形したいか（例: GitHub Releases 用リンク、既存タグとの同期など）を教えてください。
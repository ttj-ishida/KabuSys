# Changelog

すべての重要な変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

全般:
- 日付はコミット／リリース相当日を使用しています（推測）。
- 本CHANGELOGはコードベースの内容から機能追加・設計方針を推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 初期公開: KabuSys 自動売買システムの基本コンポーネント群を追加。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
  - エントリスクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading モードをサポート（paper_trading 時は MockBrokerClient を使用し、専用 SQLite（デフォルト data/paper_trading.db）へ記録して本番と分離）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
  - 設定管理
    - config.py: .env 自動読み込み機能を実装（優先度: OS 環境 > .env.local > .env）。プロジェクトルート検出は .git または pyproject.toml により行う。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。export 構文・クォート・コメント含む .env パースの堅牢化。Settings クラスを提供し、各種環境変数をプロパティ経由で取得（DB パス、PID/KILL フラグパス、Paper Trading 設定、しきい値等）。
    - 新たに参照される環境変数（代表）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - OPENAI_API_KEY
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - PAPER_FILL_MODE
      - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
      - KABUSYS_ENV, LOG_LEVEL
  - 監視（Monitoring）
    - monitoring_db の初期化呼び出し（init_monitoring_db）を各起動スクリプトに組み込み、監視用テーブルの存在を冪等に保証。
    - SystemMonitor を用いた定期チェックループ（例外発生時はログ出力して次ループへフォールスル）。
  - Execution（発注系）
    - ExecutionEngine 起動周りの組み立て処理（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を追加。RiskConfig のデフォルトパラメータを設定し、初期ポートフォリオ値を broker.get_available_cash() から取得して設定。
    - Paper Trading モード時の DB 分離を実装（settings.is_paper 判定により別 sqlite_path を使用）。
  - ポートフォリオ構築（portfolio）
    - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に合わせてスケーリング）、cost_buffer を考慮した保守的見積りを実装。
  - 研究（research）
    - factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB 経由で実装。価格・財務テーブルを参照して日毎に (date, code) ベースの結果を返す設計。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を追加。外部依存を最小化して標準ライブラリのみで実装。
    - research パッケージの __all__ を整備。
  - AI（ニュース NLP）
    - ai/news_nlp.py: raw_news と news_symbols を基に OpenAI API（gpt-4o-mini を想定）へ一括バッチ送信して銘柄別センチメントスコアを ai_scores テーブルへ書き込む機能を追加。処理はバッチ単位（最大 20 銘柄）、記事数・文字数上限（1 銘柄あたり最大記事数/文字数）を設定。API エラー（429/タイムアウト/5xx 等）に対して指数バックオフでリトライ、レスポンスを厳密にバリデーション、スコアは ±1.0 にクリップして保存。日付ウィンドウは JST ベースで定義（前日 15:00 JST 〜 当日 08:30 JST を対象）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH や --db オプションで DB ファイルを指定可能。各指標の閾値（稼働率 99%、成功率 90% 等）を定義。
  - ユーティリティ
    - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows (psutil.HIGH_PRIORITY_CLASS 等) と POSIX 系（nice 値）を吸収。set_process_priority("high"|"normal"|"low")、set_cpu_affinity を提供。権限不足や未対応 OS では警告を出してスキップするフェールセーフを実装。

### Changed
- 設計方針（初期実装段階での明記）
  - ファクター計算・研究モジュールは DuckDB 接続を受け取り、外部 API や本番取引 API へはアクセスしない方針を明確化（安全性・再現性重視）。
  - ランタイムでの直近日取得（datetime.today/date.today）を避ける設計方針を ai/news_nlp 等で採用（ルックアヘッドバイアス回避）。
  - .env パースの挙動改善: export プレフィックス対応、クォート内のエスケープ解析、コメント処理の改善を行い .env ファイル解釈を堅牢化。
  - run_monitoring は監視用途の DB 初期化を確実に行うように init_monitoring_db を呼ぶ点を明確化。

### Fixed
- ロバスト性向上（フェイルセーフ）
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続し、ログを残して次回のポーリングに進むようにした（監視プロセスの自己回復性向上）。
  - process_priority / set_cpu_affinity で権限エラーや未実装例外を捕捉し警告して処理を継続するようにした。
  - tools/paper_verification_report のクエリでテーブル未存在時に sqlite3.OperationalError を捕捉して欠損データを安全に扱う実装。
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバック（警告ログを出力）。

### Security
- 環境変数の自動読み込みはデフォルトで有効だが、テストや特殊用途向けに KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能とし、OS 環境変数の保護を考慮（.env 読み込み時の protected set 処理）。

### Notes / Implementation details
- DB: SQLite（監視・Paper Trading 用）と DuckDB（時系列・分析用）を併用する設計。各起動スクリプトは最後に接続を確実に close する実装。
- Paper Trading: run_execution は settings.is_paper を見て paper_sqlite_path を使用。実際のブローカーは BrokerClientFactory で抽象化され、Paper モードでは MockBrokerClient を返す想定。
- ロギング: 各モジュールで logging を利用しデバッグ/情報/警告を適切に出力するよう実装。
- ドメイン知識: PortfolioConstruction.md、StrategyModel.md 等を参照した設計コメントが複数のモジュールに含まれており、実装はこれらドキュメントのセクションに準拠している（コード内コメントとして記載）。

---

この CHANGELOG はソースコードの状態から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。
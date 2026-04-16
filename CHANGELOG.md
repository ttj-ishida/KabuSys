# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。重要な挙動・環境変数・運用上の注意点は各リリースノート末尾の「注記」に記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-16

### Added
- 初回公開リリース。
- アプリケーション基盤
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理（kabusys.config）
  - 環境変数/`.env` ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - `.env` と `.env.local` の読み込み順、OS 環境変数の保護機能を実装（override / protected）。
  - エクスポート形式やクォートを含む行、インラインコメントなどを考慮した堅牢な .env パーサーを実装。
  - 必須変数チェック `_require`、各種設定プロパティ（DB パス、Paper Trading 設定、監視閾値、環境種別等）を提供。
  - 環境変数で制御できる設定:
    - KABUSYS_ENV (development | paper_trading | live)
    - KABUSYS_DISABLE_AUTO_ENV_LOAD
    - PAPER_FILL_MODE (instant|partial|never|reject)
    - PAPER_TRADING_SQLITE_PATH, SQLITE_PATH, DUCKDB_PATH など
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority(level)` を実装。
  - CPU affinity 固定用 `set_cpu_affinity(cpu_count)` を実装。
  - 権限不足や未対応 OS に対する安全なフォールバック（警告ログ）を実装。
- 実行系エントリスクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 環境に応じた DB 分離（paper_trading 環境なら専用 DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag の検知で停止する制御。
    - PID ファイル出力用 path（data/execution.pid）。
    - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、例外発生時もログを残して継続する堅牢化。
    - 起動時にプロセス優先度を "high" に設定。
- モジュール: portfolio（銘柄選定・配分・サイズ計算）
  - portfolio_builder: シグナルのランク付け・候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中除外ロジック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装（risk_based / equal / score の配分方式、単元丸め、aggregate cap スケーリング、cost_buffer 考慮等）。
  - ポートフォリオ関連の純粋関数群は DB を参照せずメモリ計算のみで動作する設計。
- 研究（research）モジュール
  - factor_research: DuckDB を利用したファクター計算（momentum / volatility / value）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離の計算（ウィンドウ不足時は None）。
    - Volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率など。
    - Value: raw_financials と prices_daily を組み合わせた PER, ROE 計算（target_date 以前の最新財務データ取得）。
  - feature_exploration:
    - 将来リターン計算(calc_forward_returns)、IC（Spearman ランク相関）計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク関数(rank) を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。
  - research パッケージ初期エクスポートで zscore_normalize（kabusys.data.stats）を再エクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news テーブルから記事を集約し、OpenAI（gpt-4o-mini）に対して銘柄ごとのセンチメントスコアをバッチ送信して ai_scores テーブルに書き込む設計を実装。
  - バッチサイズ、記事/文字数トリミング、JSON 出力厳格化、429/ネットワーク/5xx のための指数バックオフ・リトライ、スコアの ±1.0 クリップなどの堅牢化を導入。
  - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
  - score_news の引数で API キーを明示可能（環境変数 OPENAI_API_KEY にフォールバック）。
  - （注）このファイルはスナップショット内で末尾が切れており、処理の一部実装が未完（_fetch_articles 以降の処理が存在しない断片あり）。
- 運用ツール
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力する CLI（--from/--to/--db オプション対応）。
    - データ不足やテーブル未存在時の安全なハンドリングを実装。
- DB 周辺ユーティリティ
  - monitoring_db.init_monitoring_db を利用して必要な監視テーブルを冪等に初期化（run_monitoring / run_execution で使用）。
- パッケージ構成に関する軽微なファイル追加（__init__.py 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キー取り扱いについては、score_news は API キーを直接引数で渡すか環境変数から解決する実装。キーをログに出力しない運用指示が必要。

---

注記（運用上の重要ポイント）
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルートにある `.env` と `.env.local` が読み込まれます。テスト等で自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB の分離
  - run_execution は paper_trading 環境であれば PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を使用し、本番 SQLite DB と分離します。
  - run_monitoring は常に settings.sqlite_path（本番の monitoring DB）を使用します（監視データは環境に依存させない方針）。
- 停止フラグ / PID 管理
  - 停止フラグ: data/stop_requested.flag（プロジェクトルート基準）を検知したら実行ループを停止します。
  - ExecutionEngine の PID ファイルは data/execution.pid（設定で変更可）。
- MONITOR_POLL_INTERVAL
  - 監視スクリプトのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能。1 秒未満や 0 以下の不正値は無視され、デフォルト 60 秒にフォールバックします。
- OpenAI ニュース NLP
  - AI モジュールは外部 API に依存するため、API の利用量・レート制限に注意してください。スナップショット内の実装ではレスポンス検証・部分的なトランザクション置換（DELETE→INSERT）を行う設計になっていますが、score_news の一部処理が未完であるため本番投入前に完全実装と十分なテストを行ってください。
- 権限とプラットフォーム差分
  - process priority / cpu_affinity の設定はプラットフォームや実行ユーザの権限に依存します。権限不足時は警告ログを出してスキップします。
- ログレベルと例外ハンドリング
  - 長時間稼働するループ処理（監視・実行エンジン）は例外発生時にログを残して継続するよう設計されていますが、重大な例外やリソースリークがないか監視を行ってください。

以上。追加・修正点の詳細や運用上の移行手順が必要であれば、その点に絞って追記します。
# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このファイルは、提供されたコードベースの内容から推測して作成した初期リリース相当の変更履歴です。

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ情報: kabusys/__init__.py にバージョン 0.1.0 を追加。
- 環境/設定管理
  - Settings クラスを追加（src/kabusys/config.py）。.env 自動ロード機構、.env/.env.local の優先度、保護された OS 環境変数の扱いを実装。
  - .env パーサを実装（引用符・エスケープ・export 構文・インラインコメント対応）。
  - 各種設定プロパティを実装（J-Quants / kabu / LINE / DB パス / PID/KILL フラグ /閾値 /環境判定 等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- 実行用スクリプト
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、Broker クライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、engine.run_session 呼び出し）。
    - Paper Trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
    - RiskManager のデフォルト設定を含む RiskConfig を組み込み。initial_portfolio_value を broker.get_available_cash() から初期化。
  - 監視ポーリング起動スクリプト run_monitoring.py を追加。
    - プロセス優先度設定、監視用 SQLite（monitoring）初期化、DuckDB 接続、SystemMonitor のループ起動。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用する旨を明記。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db の利用箇所を追加）。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX(Linux, macOS, FreeBSD) に対応した優先度設定（high/normal/low）。
    - CPU affinity を指定コア数にピン留めする set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は安全にログ warning してスキップ。
- Portfolio 構築ロジック
  - 候補選定（select_candidates）、等重配分 / スコア加重（calc_equal_weights, calc_score_weights）を追加（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
  - 株数決定ロジック（calc_position_sizes）を追加（src/kabusys/portfolio/position_sizing.py）。risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer の考慮等を実装。
  - portfolio パッケージのエクスポートを設定（src/kabusys/portfolio/__init__.py）。
- リサーチ機能（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、出来高・売買代金指標）
    - calc_value（PER、ROE の算出。raw_financials 結合）
    - DuckDB を用いた効率的なウィンドウ集計クエリを採用
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（将来リターンの一括取得）
    - calc_ic（Spearman ランク相関による IC 計算）
    - rank / factor_summary（ランク変換、統計サマリ）
  - research パッケージのエクスポートを設定（src/kabusys/research/__init__.py）。
- AI ニューススコアリング
  - OpenAI（gpt-4o-mini）を用いたニュース NLP スコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース時間ウィンドウ計算、記事集約、銘柄ごとのテキストトリム、最大バッチサイズ、スコアクリッピング、リトライ（429/5xx/タイムアウト/接続障害）と指数バックオフ、レスポンスバリデーション、部分成功時の安全な DB 更新戦略を実装。
- Paper Trading 検証ツール
  - paper_verification_report.py を追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を算出する CLI ツール。
    - データ不在時の安全なハンドリング（OperationalError 捕捉）や P95 計算実装。
    - 判定基準（閾値）を定義して PASS/FAIL を出力。
- DB 接続
  - sqlite3 と DuckDB を併用する設計。run スクリプトとモジュールで接続・クローズを適切に扱う。

### Changed
- ログの基本設定をエントリポイント側で行う（run_monitoring.py / run_execution.py で logging.basicConfig(level=logging.INFO)）。
- run_execution/run_monitoring の起動フローで起動時にプロセス優先度を最初に設定するように統一。
- 環境変数のバリデーションを強化（Settings の env / log_level / PAPER_FILL_MODE 等で不正値時に明示的な例外を発生）。

### Fixed
- MONITOR_POLL_INTERVAL の不正（0 以下や非整数）を検出して警告を出し、デフォルトにフォールバックする処理を追加（run_monitoring.py）。
- .env パーサの引用符内エスケープ、インラインコメント処理、export 形式対応により .env 読み込みの堅牢性を向上（config.py）。
- position_sizing の aggregate cap スケーリングで端数処理・残余配分をより再現性を保って処理するロジックを実装（position_sizing.py）。
- research / factor 計算においてウィンドウ不足時に None を返すことで安全に扱えるように調整（factor_research.py）。
- paper_verification_report の P95 算出、空データハンドリングを実装（tools/paper_verification_report.py）。

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から取得し、未設定時は ValueError を発行して処理を中断。キーの露出を避ける設計。

### Notes / Known limitations
- 一部の TODO がコード中に残っている（例: position_sizing の銘柄別 lot_size サポート、apply_sector_cap の価格フォールバック戦略）。
- news_nlp の処理は外部 API（OpenAI）に依存するため、API の利用制限やコストに注意が必要。
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計のため、運用時には意図した DB パス設定に注意。
- set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでスキップされる。ログで警告される。

---

（本 CHANGELOG はコードベースの静的解析・コメント・実装内容から推測して生成しています。実際のコミット履歴や意図された変更履歴とは差異がある可能性があります。）
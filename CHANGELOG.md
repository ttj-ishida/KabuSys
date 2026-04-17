# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。

## [0.1.0] - 2026-04-17

### 追加
- 全体
  - 初期リリース。パッケージメタ情報を src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 実行・監視（ファイル: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
  - 実行エンジン起動スクリプト run_execution を追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離する挙動をサポート。
    - 実行用の PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全な停止、バックグラウンドスレッドでの engine.run_session 実行とタイムリーな停止処理を実装。
    - ExecutionEngine の起動前に監視テーブルが存在することを保証するため init_monitoring_db を呼び出す。
    - デフォルトの RiskConfig を組み込み、BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を構成する例を含む。
  - システム監視起動スクリプト run_monitoring を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトへフォールバックして警告を出力。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、check_once() 実行中の例外はログに記録して次サイクルへ継続。
    - 監視はアプリケーション実行環境に関わらず本番 sqlite_path を使用する仕様。
  - 両スクリプトとも起動直後にプロセス優先度を "high" に設定するフックを追加（src/kabusys/utils/process_priority.set_process_priority を使用）。

- 設定管理（ファイル: src/kabusys/config.py）
  - .env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env / .env.local の読み込み順を定義（OS環境変数 > .env.local > .env）、OS 環境変数は上書き保護される（protected）。
  - export KEY=val 形式および引用符付き値（バックスラッシュエスケープ対応）、インラインコメントの扱いなど堅牢な .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - Settings クラスを導入し各種設定プロパティを提供:
    - J-Quants / kabu / LINE / DB パス（duckdb_path, sqlite_path, paper_sqlite_path）など。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant", "partial", "never", "reject"）。
    - PID / KILL フラグ関連設定（pid_file_path, kill_flag_path, kill_flag_clear_on_start）。
    - 監視閾値（cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）および短縮判定ヘルパ（is_live, is_paper, is_dev）。
    - LOG_LEVEL のバリデーション。

- ツール（ファイル: src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成スクリプトを追加。
    - CLI で期間指定（--from / --to）と DB パス指定（--db）を受け取る。
    - システム稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して表示。
    - PASS/FAIL 判定の閾値を定義（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）。
    - DB が存在しない場合のエラーメッセージを出力。

- ポートフォリオ構築（ファイル: src/kabusys/portfolio/*.py）
  - 銘柄選定と重み計算（portfolio_builder）を追加:
    - select_candidates: score 降順、同点は signal_rank の昇順でタイブレークし上位 N を選択。
    - calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等金額でフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）を追加:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3、未知は 1.0 にフォールバックして警告）。
  - ポジションサイジング（position_sizing）を追加:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応して発注株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限・総投下上限、cost_buffer を用いた保守的評価、aggregate cap を超えた際のスケーリングと端数の lot 単位での再配分ロジックを実装。
  - モジュールの公開 API を package-level (src/kabusys/portfolio/__init__.py) で整理。

- ユーティリティ（ファイル: src/kabusys/utils/process_priority.py）
  - プロセス優先度設定ユーティリティを追加。
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収する実装で、psutil を利用して nice / priority を設定。
    - set_process_priority(level)（"high"|"normal"|"low"）と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未実装 API の場合は警告ログでスキップするフェイルセーフ。

- リサーチ & 特徴量（ファイル: src/kabusys/research/*.py）
  - ファクター計算モジュール（factor_research）を追加:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム・MA200乖離、ATR、avg_turnover、PER/ROE など）を計算。
    - データ不足時の None 処理、ウィンドウ幅・スキャン範囲の安全バッファを考慮。
  - 特徴量探索（feature_exploration）を追加:
    - calc_forward_returns（複数ホライズン対応、入力検証含む）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計）、rank（同順位は平均ランク）を提供。
    - 外部ライブラリに依存せず標準ライブラリ + duckdb で実装。
  - research パッケージエクスポートを整理（zscore_normalize を含む）。

- AI ニュース NLP（ファイル: src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI (gpt-4o-mini) に投げて銘柄別センチメント ai_score を生成するスコアリングモジュールを追加（DuckDB を参照）。
    - タイムウィンドウの計算（前日15:00 JST〜当日08:30 JST を UTC で扱う）ユーティリティを実装。
    - 銘柄ごとに記事を集約し、トークン肥大化対策として記事数・文字数をトリムする設定を持つ（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズ・リトライ（429/ネットワーク/5xx 共通）と指数バックオフ、レスポンスバリデーション、スコアクリップ（±1.0）、部分成功時に既存スコアを保護するための限定的な DB 書き換え戦略を採用。
    - OpenAI API キーの引数/環境変数解決をサポート。API 未設定時は ValueError を送出。
    - （注）実装ファイルは長いため一部省略（が主要設計・安全策は上記に含む）。

- DB 初期化ユーティリティ（参照: src/kabusys/monitoring/monitoring_db.py を呼出）
  - run_* スクリプトで監視テーブルの冪等な初期化を保証する init_monitoring_db の利用を標準化。

### 変更
- - （本リリースは新規追加が中心のため、既存機能の互換破壊は意図していません）

### 修正
- - （本リリースでは特定のバグ修正履歴は含まれていません）

### 既知の注意事項 / TODO
- portfolio.position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨をコメントで残しています。
- ai.news_nlp:
  - 実行時に外部 OpenAI API を使用するため API キーと API レート制御に注意が必要。
- config._find_project_root:
  - プロジェクトルートが検出できない場合は自動 .env 読み込みをスキップする仕様。テスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

---

（必要に応じて今後のリリースでは各機能のユニットテスト追加やエラーハンドリングの強化、ドキュメントの拡充を予定しています。）
# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-13

### 追加
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
  - パッケージメタ:
    - バージョン定義: src/kabusys/__init__.py (__version__ = "0.1.0")
  - 設定管理:
    - .env ファイルおよび環境変数から設定を読み込む自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。（src/kabusys/config.py）
    - 自動読み込みを無効にするための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値など）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV のバリデーション（"development" | "paper_trading" | "live"）。
  - 実行/監視用エントリポイント:
    - run_execution.py: ExecutionEngine 起動スクリプト。Paper Trading モード時は専用 SQLite（data/paper_trading.db）と MockBrokerClient を利用し、本番 DB と分離。（src/kabusys/run_execution.py）
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照する点に注意。（src/kabusys/run_monitoring.py）
    - 両スクリプトとも起動直後にプロセス優先度を "high" に設定する処理を組み込み（src/kabusys/utils/process_priority.py を使用）。
  - データベース / 分析基盤:
    - DuckDB および SQLite 接続を利用し、prices_daily / raw_financials などのテーブルに対する分析を想定。（複数のモジュールで使用）
  - Portfolio 構築ユーティリティ（純粋関数群: DB 非依存、メモリ内計算）:
    - 候補選定: select_candidates（スコア降順、signal_rank でタイブレーク）。（src/kabusys/portfolio/portfolio_builder.py）
    - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）。（src/kabusys/portfolio/portfolio_builder.py）
    - セクター集中制限: apply_sector_cap（既存ポジションのセクター比率が閾値を超える場合に新規候補を除外）。unknown セクターは上限適用対象外。（src/kabusys/portfolio/risk_adjustment.py）
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数、未知値は 1.0 でフォールバック）。（src/kabusys/portfolio/risk_adjustment.py）
    - 株数決定: calc_position_sizes（risk_based / equal / score の allocation_method をサポート、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り等）。（src/kabusys/portfolio/position_sizing.py）
  - リサーチ / ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（window の行数が足りない場合は None）。（src/kabusys/research/factor_research.py）
    - calc_volatility: ATR(20), 相対 ATR, 20 日平均売買代金, 出来高比率。True Range の NULL 伝播を考慮。 （src/kabusys/research/factor_research.py）
    - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新レコードを取得）。（src/kabusys/research/factor_research.py）
    - calc_forward_returns, calc_ic, factor_summary, rank: 将来リターン、IC（Spearman）、統計サマリ、ランク変換等の探索用ユーティリティ。（src/kabusys/research/feature_exploration.py / src/kabusys/research/__init__.py）
    - zscore_normalize は data.stats からエクスポートして再利用可能に。
  - AI / ニュース NLP:
    - news_nlp モジュールにて raw_news を OpenAI API (gpt-4o-mini) へバッチ送信して銘柄ごとのセンチメント ai_score を生成、ai_scores テーブルへ書き込む機能を実装。（src/kabusys/ai/news_nlp.py）
    - 機能: タイムウィンドウ計算（JST 基準 → UTC）、銘柄毎記事集約（記事数・文字数上限でトリム）、最大 20 銘柄/チャンクで API コール、429/ネットワーク/5xx は指数バックオフでリトライ、レスポンスバリデーション、スコア ±1.0 にクリップ、部分失敗時に既存スコアを保護するため対象 code 絞り込みで置換書き込み。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError）。
  - ユーティリティ:
    - process_priority: Windows/Linux/macOS を抽象化してプロセス優先度および CPU affinity を設定するユーティリティを実装。権限不足や未対応 OS の場合は安全にスキップし警告ログを出力。（src/kabusys/utils/process_priority.py）
  - ツール:
    - paper_verification_report: Paper Trading の検証レポート生成スクリプト。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。DB パスは環境変数または --db オプションで指定可。（src/kabusys/tools/paper_verification_report.py）

### 変更
- なし（初期リリース）。

### 修正（注意・挙動の明示）
- run_monitoring のポーリング間隔読み取りで不正な MONITOR_POLL_INTERVAL 値を検出した場合は警告を出しデフォルト（60 秒）にフォールバックするように実装。（src/kabusys/run_monitoring.py）
- SystemMonitor の監視ループにおいて check_once() 内の例外は捕捉してログに例外情報を出力後、次のポーリングまで待機するようフェイルセーフに設定。（src/kabusys/run_monitoring.py）
- run_execution/run_monitoring で使用する DB 接続（SQLite / DuckDB）は finally ブロックで必ずクローズするように実装し、プロセス終了時のリソースリークを防止。（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
- apply_sector_cap: unknown セクターの銘柄はセクター制限の適用対象外とする挙動を明示。（src/kabusys/portfolio/risk_adjustment.py）
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし警告ログを出力。（src/kabusys/portfolio/portfolio_builder.py）
- calc_position_sizes:
  - lot_size 単位で丸める処理、per-position および aggregate 上限、available_cash によるスケーリング処理を丁寧に実装。
  - price 欠損時は該当銘柄をスキップし、デバッグログを出力する挙動を追加。（src/kabusys/portfolio/position_sizing.py）
- settings の .env パーサは export 文やクォート、インラインコメント等の一般的な .env 形式に対する堅牢な解析を実装。読み込み順序は OS 環境 > .env.local > .env。OS 環境変数は protected として上書きされない。（src/kabusys/config.py）
- news_nlp:
  - OpenAI クライアント呼び出しでのバッチ処理・リトライ・レスポンス検証・クリッピングなどを実装し、部分的な API 失敗でもシステム全体が停止しないよう設計。（src/kabusys/ai/news_nlp.py）
  - target_date に基づくニュースウィンドウ計算を純粋関数 calc_news_window として切り出し、テスト可能性を向上。（src/kabusys/ai/news_nlp.py）
- paper_verification_report:
  - 空データやテーブル未作成時に sqlite3.OperationalError を扱うフォールバックを追加し、欠損状況でもレポート実行が継続可能。（src/kabusys/tools/paper_verification_report.py）

### 既知の制約 / 注意点
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用パス）を使用します。Paper Trading 実行時の監視 DB は分離されませんので運用上の注意が必要です（run_monitoring の挙動）。
- process_priority の適用は権限（Linux の nice のマイナス値など）や OS に依存し、失敗時は警告を出して処理を継続します。
- DuckDB に関する注意: executemany に空 params を渡すとバージョン依存で問題があるため、実装側で空の params を避ける配慮が必要（news_nlp のコメント等に留意）。
- 一部ロジック（価格欠損時のフォールバック価格や lot_size の将来的拡張等）は TODO コメントで拡張余地あり。

### 削除
- なし

### 廃止予定
- なし

---

今後のリリースでは、実装の補完（例: 銘柄別 lot_size の導入、価格フォールバックロジック、より詳細な監視メトリクス保存など）やテストカバレッジ拡充を予定しています。
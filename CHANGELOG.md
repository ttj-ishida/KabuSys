Keep a Changelog に準拠した CHANGELOG.md（日本語）
全ての注目すべき変更を記録します。フォーマット: https://keepachangelog.com/ja/

Unreleased
----------
- なし

[0.1.0] - 2026-04-13
--------------------
Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - 基本情報
    - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
  - 設定管理 (kabusys.config)
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env / .env.local の読み込み（OS 環境変数保護、override 制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - 独自の .env パーサ実装（export 形式、クォート・エスケープ、インラインコメント対応）。
    - 各種環境変数のプロパティ化と検証:
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL の検証
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）
      - デフォルトパス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など
      - 監視閾値: CPU/MEM/DISK のしきい値プロパティ
  - 実行/監視用エントリポイント
    - run_execution.py
      - プロセス優先度を "high" に設定して起動。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite (data/paper_trading.db デフォルト) を使用して本番 DB と分離（ドキュメント化）。
      - DuckDB 接続を受け、ExecutionEngine を組み立てて実行。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる。
      - RiskConfig による初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）、初期ポートフォリオ値は broker.get_available_cash() を利用。
      - finally ブロックで DB を確実にクローズ。
    - run_monitoring.py
      - プロセス優先度を "high" に設定して起動。
      - 監視ループは Monitoring 用 DB（sqlite_path）を環境にかかわらず本番 sqlite_path を使用して接続・初期化。
      - DuckDB も併用。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - check_once() 実行時の例外をキャッチしてログに残し次ポーリングへ継続。KeyboardInterrupt での正常終了をサポート。
  - 監視 DB 初期化ユーティリティ
    - monitoring.monitoring_db.init_monitoring_db を各エントリポイントで呼び出し、監視テーブル存在を保証（冪等）。
  - ユーティリティ (kabusys.utils.process_priority)
    - set_process_priority(level) — Windows / POSIX（Linux/Mac/FreeBSD）差を吸収してプロセス優先度を設定。権限不足や未対応 OS をハンドルして警告でフォールバック。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定。入力検証と例外ハンドリングあり。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder.py
      - select_candidates: スコア降順 + signal_rank によるタイブレークで候補抽出。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター比率を計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは無視）。sell_codes による当日売却予定の除外対応。
      - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull/neutral/bear、未知のレジームは警告して 1.0 にフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - 単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）スケーリング、cost_buffer を考慮した保守的見積り、スケールダウン後の残差を基に追加配分するロジックを実装。
  - 研究用モジュール (kabusys.research)
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算。ウィンドウ/必要行数チェックでデータ不足時は None を返す。
    - feature_exploration.py
      - calc_forward_returns: 将来リターン計算（任意 horizon）。
      - calc_ic, rank, factor_summary: IC 計算（Spearman ランク相関）、ランク関数（同順位は平均ランク）、ファクター統計サマリ。
    - いずれも外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。
  - AI ニュース NLP (kabusys.ai.news_nlp)
    - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとにセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込み。
    - 特徴:
      - ニュース集計ウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）。
      - 1 チャンク最大 20 銘柄、1 銘柄につき記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ付きリトライ、最大リトライ回数の設定。
      - レスポンスの JSON バリデーション（results キー、コード・スコアの型チェック）、スコアを ±1.0 にクリップ。
      - 部分失敗に備え、書き込みは対象コードのみを絞って置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）することで他コードのスコアを保護。
      - API キー未設定時は ValueError。
  - コマンドラインツール (kabusys.tools.paper_verification_report)
    - Paper Trading の検証レポートを生成する CLI。
    - --from / --to / --db オプションで期間・DB を指定可能。デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ（avg/max/P95）を集計し、閾値判定（PASS/FAIL）を出力。
    - DB が存在しない場合やテーブルがない場合のフォールバックを実装。
    - P95 計算、フォーマットユーティリティを提供。
  - DuckDB 統合
    - 複数モジュールで DuckDB 接続を受けて SQL ベースの集計・計算を行う設計（research / ai / run_* スクリプト 等）。
  - その他
    - 各所で入力検証・例外ハンドリングを強化（不正な環境変数、DB 接続失敗、権限エラーの警告処理等）。
    - ドキュメント（各関数の docstring）を充実させ、設計上の注意点や将来的な TODO を明記。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時には明示的にエラーにして誤使用を防止。

注記
- 設定や振る舞い（特に DB パスや PAPER_TRADING の挙動、プロセス優先度設定など）は環境変数で上書き可能です。運用時は .env/.env.local と環境変数の優先順位に注意してください。
- run_monitoring.run は監視用 DB を本番 sqlite_path に接続します（意図的に環境に依存しない設計）。Paper Trading 用の発注履歴は run_execution が分離して紙の DB に記録します。運用者はこの分離に留意してください。

-- END --
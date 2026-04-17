# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。重要な新機能、挙動、注意点を日本語でまとめています。

## [Unreleased]

- 現在なし。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期バージョンのライブラリ/アプリケーションを追加（パッケージ名: kabusys, バージョン 0.1.0）。
  - パッケージのトップレベルメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。

- 実行・運用
  - 実行エントリスクリプトを追加:
    - run_execution.py: ExecutionEngine を起動し、Broker クライアント、OrderManager、RiskManager、Reconciler などの依存コンポーネントを組み立てて実行（デーモンスレッドで run_session 実行）。paper_trading 環境では paper_trading 用の SQLite DB を利用。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する（監視データは一貫して本番 DB へ記録）。

  - 監視データベース初期化ユーティリティを使用するための初期接続処理を追加（init_monitoring_db を利用）。

  - PID / 停止フラグ管理:
    - 実行プロセスの pid ファイルを扱う設定や、data 配下の stop_requested.flag を用いた外部停止制御に対応。

- 設定・環境変数管理
  - Settings クラスを追加（src/kabusys/config.py）:
    - 環境変数からアプリケーション設定を取得するプロパティ群を実装（J-Quants・kabu API、LINE、DB パス、監視閾値、環境種別など）。
    - env（KABUSYS_ENV）、log_level（LOG_LEVEL）などの検証ロジックを実装（無効値は ValueError）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）、duckdb path、pid/kill フラグパス、監視閾値（CPU/MEM/DISK）等をプロパティ化。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む。
    - .env のパースでは export 形式、シングル/ダブルクォート、エスケープ、行末コメントの考慮などに対応。
    - OS 環境変数を保護（.env.local は上書き可だが OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）:
    - set_process_priority(level: "high"|"normal"|"low"): Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count: int|None): カレントプロセスを最初の N コアに固定する機能（権限不足や未対応環境では警告を出してスキップ）。
    - 実行スクリプトは起動時に優先度を "high" に設定するよう変更。

- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（src/kabusys/portfolio/*）:
    - portfolio_builder.py:
      - select_candidates: BUY シグナルをスコア降順でソートして上位 N を抽出。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額にフォールバック（警告）。
    - risk_adjustment.py:
      - apply_sector_cap: セクター集中上限チェック。既存保有のセクター別エクスポージャーを計算して超過セクターの新規候補を除外（unknown セクターは除外しない）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（既知レジーム以外は 1.0 にフォールバック）。
    - position_sizing.py:
      - calc_position_sizes: weight / candidates / allocation_method（risk_based/equal/score）に基づき株数（lot 単位で丸め）を計算。risk_based では stop_loss_pct と risk_pct に基づくリスクベース算出。aggregate cap（available_cash）を超える場合はスケールダウンと余り配分ロジックを実装。cost_buffer による保守的コスト見積りにも対応。

- 研究・リサーチ
  - research モジュールを追加（src/kabusys/research/*）:
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily テーブルから計算。
      - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率を計算。true_range 計算における NULL 伝播を考慮。
      - calc_value: raw_financials テーブルから直近財務を取得し PER / ROE を計算（EPS が 0 や NULL の場合は None）。
    - feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）後の将来リターンをまとめて取得。
      - calc_ic: factor と forward リターンのスピアマンランク相関（IC）を計算。レコードが少ない場合は None を返す。
      - factor_summary: count/mean/std/min/max/median を算出。
      - rank: 同順位は平均ランクを付与するランク関数（round による ties 対策）。
    - research.__init__.py で zscore_normalize（data.stats）を含む公開 API を定義。

- AI / ニュース NLP
  - ai/news_nlp.py を追加（OpenAI API を利用したニュースセンチメントスコアリング）:
    - raw_news / news_symbols から対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）で記事を抽出して銘柄ごとに集約。
    - 最大記事数・文字数でトリムし、最大 20 銘柄ずつ gpt-4o-mini へバッチ送信（JSON Mode 想定）。
    - 429/ネットワーク断/5xx は指数バックオフでリトライ。レスポンスをバリデートし、スコアを ±1.0 にクリップして ai_scores テーブルへ書き込み（部分失敗時の既存スコア保護のために対象コードで削除→挿入する挙動）。
    - OPENAI_API_KEY の未設定は明示的にエラーにする設計（api_key 引数で上書き可能）。
    - 実装方針としてルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない。

- ツール
  - tools/paper_verification_report.py を追加:
    - Paper Trading の検証レポートを生成する CLI ツール。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し、Pass/Fail 判定を出力（閾値はソース内に定義: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - SQLite DB（デフォルト data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）から trade_logs / system_status / risk_logs を参照し、日付フィルタ (--from/--to) による集計をサポート。
    - P95 はソートして計算。DB が無ければエラーメッセージを出力して終了。

### Changed
- 仕様・デフォルト挙動
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する明示的な挙動を採用（監視データは常に本番 DB に記録）。
  - 実行エンジン（run_execution）は paper_trading 環境では専用の paper_sqlite_path を使用して本番 DB と完全分離する設計。

- .env 読み込み順序・保護
  - 自動ロードの優先順位は OS 環境変数 > .env.local > .env（.env.local は override=True）。OS 環境変数は protected として上書き不可。

### Fixed
- 入力パースや計算の堅牢性向上（既知のケースをハンドリング）
  - config._parse_env_line: export プレフィクス、クォート内のバックスラッシュエスケープ、行内コメント処理などを正しくパースするように実装。
  - factor_research / volatility: true_range の NULL 伝播を明確にし、欠損データの扱い（カウント閾値）を厳密化。
  - position_sizing: lot 単位の丸め、aggregate cap スケーリング時の余り配分ロジックを実装し、可再現性のためソート安定性を確保。

### Security
- 環境変数の機密情報（API キー等）は Settings 経由で取得する設計。自動 .env ロードは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Migration
- 実行に必要な外部依存:
  - psutil（process_priority）、duckdb、openai（news_nlp）などが必要。
- 環境変数の主な設定キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, PAPER_TRADING_SQLITE_PATH, SQLITE_PATH, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL, MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）など。
- MONITOR_POLL_INTERVAL:
  - 0 以下や不正な値が設定された場合は警告を出してデフォルト（60 秒）にフォールバックする。
- PAPER_FILL_MODE:
  - 有効値は "instant" | "partial" | "never" | "reject"。不正な値は ValueError。

---

開発・運用上の詳細（実装コメント、TODO、設計メモ）は各ソースファイル内の docstring / コメントに記載されています。必要であれば、特定モジュールごとの詳細なリリースノートや移行ガイドを作成します。
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ骨格を追加（初期リリース）。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実行用エントリポイントを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して初期化。
    - プロセス優先度を起動時に "high" に設定。
    - SQLite / DuckDB 接続の初期化とクリーンアップ処理を実装。
  - run_execution.py
    - ExecutionEngine（トレード実行）の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - 実行開始前に監視テーブルを冪等に初期化（init_monitoring_db）。
    - プロセス優先度を起動時に "high" に設定。
- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 等）。
  - バリデーション実装: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック。
- Portfolio 関連の純粋関数群を追加（銘柄選定・配分・リスク調整・株数決定）。
  - portfolio_builder.py
    - select_candidates: スコア降順・タイブレーク処理を実装。
    - calc_equal_weights, calc_score_weights（スコア全て 0.0 の場合は等金額配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限。既存保有のセクターエクスポージャー計算と候補の除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に合わせたスケーリング）、cost_buffer（手数料・スリッページ保守見積）を実装。
    - 不足価格データの扱い（スキップ）や安全弁付きの残余配分アルゴリズムを実装。
- 研究（research）モジュールを追加（DuckDB を利用したファクター計算・解析）。
  - factor_research.py
    - calc_momentum、calc_volatility、calc_value を実装。prices_daily / raw_financials を参照し、欠損やデータ不足時の挙動を考慮。
  - feature_exploration.py
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、rank、factor_summary を実装。
    - 外部依存を排し標準ライブラリのみで実装。
  - research パッケージの __all__ を整備し、zscore_normalize との統合を提供。
- AI ニュース NLP モジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news から銘柄別にニュースを集約し OpenAI (gpt-4o-mini) でセンチメントをスコア化して ai_scores に書き込むワークフローを実装。
  - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、JSON 出力検証、スコアの ±1.0 クリップ等を実装。
  - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。API キー未設定時は例外を送出。
  - ニュース収集ウィンドウ計算（JST ベース→UTC 変換）機能を実装。
- ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - set_process_priority: Windows/POSIX の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
  - set_cpu_affinity: プロセスを先頭 N コアに固定する機能を追加（None の場合はスキップ）。
  - 権限不足や未対応プラットフォームは警告を出してスキップする安全設計。
- 監視 DB 初期化ユーティリティを追加（monitoring.monitoring_db:init_monitoring_db が参照される）。
- ツールスクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - Paper Trading 用の検証レポート生成スクリプトを実装。
  - コマンドライン引数 --from/--to/--db に対応。デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
  - 稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計し PASS/FAIL 判定を出力（閾値はスクリプト内定義）。
  - DB のテーブル欠損時に安全に N/A を返す設計。
- DuckDB と SQLite を組み合わせたデータ設計を採用。
  - DuckDB を時系列・ファクタ計算用に使用（prices_daily / raw_financials 等）。
  - SQLite を監視・発注ログ用に使用（monitoring / trade_logs / risk_logs 等）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は明示的にエラーにすることで誤動作を防止。

Notes / Migration / 環境変数のポイント
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後や CWD 依存回避のため）。
- 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- 監視プロセスのポーリング間隔: MONITOR_POLL_INTERVAL（秒）。無効な値や 0 以下はデフォルト 60 秒にフォールバック。
- Paper Trading 関連:
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用。
  - PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"（不正値は例外）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite(監視): data/monitoring.db
  - SQLite(paper_trading): data/paper_trading.db
- PID / kill フラグ関連の設定プロパティを Settings で提供（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- プロセス優先度設定は起動直後に呼び出される。権限不足等で設定できない場合は警告が出るが継続する。

今後の改善案（TODO）
- 銘柄別 lot_size を stocks マスタに持たせる拡張（position_sizing の TODO）。
- price 欠損時のフォールバック（前日終値や取得原価）実装（risk_adjustment の TODO）。
- ai/news_nlp の部分失敗時の DB トランザクション粒度のさらなる堅牢化。
- モニタリング・実行のユニットテスト追加（特に DB 初期化・例外パス）。
- DuckDB の executemany 周りの制約に合わせた最適化や大規模データ処理チューニング。

---
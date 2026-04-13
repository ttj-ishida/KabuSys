CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初期リリースとして以下の主要コンポーネントを追加。
  - パッケージメタ情報: __version__ = "0.1.0" を定義。

- 実行 / オーケストレーション
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。
    - BrokerClientFactory を介してブローカークライアントを生成（環境に応じてモック/本番を切替）。
    - Paper trading 環境（KABUSYS_ENV=paper_trading）では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ExecutionEngine の起動前に監視テーブルを初期化（冪等）。
    - RiskManager / OrderManager / Reconciler 等の組み立てと、デフォルトの RiskConfig を提供。
    - プロセス優先度を起動時に "high" にセット（utils/process_priority を利用）。

  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して記録。
    - DB 初期化（init_monitoring_db）、DuckDB との接続、PID ファイル管理をサポート。
    - 例外発生時はログに残して次回ポーリングへ継続（フェイルセーフ）。KeyboardInterrupt を捕捉して正常終了。

- 設定 / 環境
  - config.py：環境変数・設定管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export KEY=val、クォート文字列（バックスラッシュエスケープ）やインラインコメントを正しく処理。
    - OS 環境変数を保護して .env.local の上書きを制御。
    - Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視 / システム設定などのプロパティを型変換・検証付きで取得可能（必須変数未設定時は ValueError を送出）。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装。

- モニタリング / ツール
  - monitoring_db 初期化ユーティリティ（init_monitoring_db を利用）。
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成 CLI を追加。
    - --from / --to / --db オプションで期間と DB を指定可能。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計して人間向けレポートを出力。
    - 指標の閾値（稼働率 99%、注文成功率 90% 等）による PASS/FAIL 判定を実装。
    - DB が存在しない / テーブルがない場合は安全にハンドリングして N/A を表示。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py：候補選定と重み計算（等金額 / スコア加重）を実装。
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（全銘柄スコアが 0 の場合は等金額へフォールバックして警告）。

  - portfolio/risk_adjustment.py：
    - apply_sector_cap: 既存保有・価格情報を元にセクター集中上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py：
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した株数算出ロジックを実装。
    - 単元株（lot_size）単位で丸め、per-position 上限・aggregate cap（available_cash）に基づくスケーリング、残余キャッシュでの端数再配分アルゴリズムを実装。
    - cost_buffer を考慮した保守的なコスト見積りをサポート。
    - 価格欠損時のスキップやログ出力を実装（TODO: 価格フォールバック戦略の注記あり）。

- 研究 / ファクター
  - research/factor_research.py：DuckDB を用いたファクター計算を追加（Momentum / Volatility / Value）。
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials テーブルを参照してファクターを計算。
    - 各関数は target_date を引数に取り、欠損データ時は None を返すなど安全設計。

  - research/feature_exploration.py：
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（horizons の検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman の ρ）計算、ランク変換、基本統計量サマリーを標準ライブラリのみで実装（pandas 等に非依存）。

- AI / ニュース解析
  - ai/news_nlp.py：OpenAI を使ったニュース記事のセンチメントスコアリングを実装。
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST → UTC 変換）を計算。
    - score_news: raw_news / news_symbols を集約し、最大 20 銘柄ずつ gpt-4o-mini へバッチ送信して JSON レスポンスをパース・バリデーションのうえ ai_scores テーブルへ部分置換で書き込み。
    - トークン肥大化対策（1 銘柄あたり最大記事数・最大文字数）と、429/ネットワーク/5xx に対する指数バックオフ・リトライ実装。
    - API キー未指定時は ValueError を送出。API 失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。

- ユーティリティ
  - utils/process_priority.py：
    - set_process_priority: Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX 系（nice 値）を吸収してプロセス優先度を設定。未対応 OS は警告してスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能（エラー時は警告してスキップ）。
    - 権限不足等による例外（AccessDenied 等）は警告ログで安全に無視。

Changed
- （初期リリースのため特記事項なし）

Fixed
- config._get_poll_interval 相当の検証・フォールバック実装により、無効な MONITOR_POLL_INTERVAL が設定された場合に ValueError を避けてデフォルトで動作するようになった（警告ログ出力）。

Deprecated
- （なし）

Removed
- （なし）

Security
- Settings.require により、JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等の必須環境変数が未設定の場合は明示的に ValueError を送出するようになり、起動時に不足を検知できる。
- .env 自動ロード時に OS 環境変数を保護（上書き禁止）する仕組みを導入。

Notes / Limitations / TODO
- position_sizing.calc_position_sizes:
  - 価格が欠損（0.0）の場合にエクスポージャーを過少見積りしてブロックが外れる可能性があるため、前日終値や取得原価などのフォールバック価格を将来的に検討する TODO が残る。
- ai/news_nlp:
  - DuckDB への executemany 前に params が空でないことを確認する必要性がコードコメントとして明示されている（DuckDB のバージョン依存制約への配慮）。
- 実運用上の権限（プロセス優先度変更や CPU affinity 設定）により、psutil の AccessDenied が発生する可能性があり、その場合は警告を出してスキップする設計。
- OpenAI 連携は外部 API に依存するため、API の制限や料金に注意すること。

参照
- 各モジュールの実装内コメント（PortfolioConstruction.md / StrategyModel.md 等）に設計参照箇所や運用上の注意を記載しています。
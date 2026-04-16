CHANGELOG
=========

すべての重要な変更履歴をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

ルール:
- 可能な限りコードから推測して記載しています。
- 日付は本スニペット取得時点（2026-04-16）を用いています。

[Unreleased]
-------------

- 現状、特になし。主要な機能は 0.1.0 として導入されていますが、news_nlp モジュールの一部（記事取得のマップ作成処理）がスニペット内で途切れているため、実装完了・テスト・堅牢化は継続作業として残っています。

[0.1.0] - 2026-04-16
--------------------

Added
- プロジェクト初期リリース（バージョン 0.1.0）。
- アプリケーション設定管理
  - kabusys.config.Settings を導入。
  - .env / .env.local の自動ロード機構（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。OS 環境変数を保護するための上書き制御を提供。
  - .env の行パーサーは export 形式、引用符付き値、インラインコメント等に堅牢に対応。
  - 多数の設定プロパティを定義（J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境種別判定など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。

- 実行関連スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、スレッド駆動のセッション実行・停止制御を実装。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義し、初期ポートフォリオ値をブローカーから取得して初期化。

  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効な値は警告してデフォルトにフォールバック）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に "high" に設定（utils/process_priority を使用）。
    - 停止フラグ検知と例外ハンドリングによりループの堅牢性を確保。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルが存在することを冪等に保証（両スクリプトで実施）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中度チェック（既存保有を時価ベースで集計し閾値超過セクターの新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に対応した発注株数算出、lot（単元）丸め、per-stock 上限・aggregate cap（利用可能現金に合わせたスケールダウン）処理、cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケールダウン時に端数処理（残余キャッシュを用いた lot 単位での追加配分）を実装。

- リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率の計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（SQL で効率的に取得）。
    - calc_ic: スピアマンのランク相関（IC）を実装（null / 非有限値を除外、サンプル少数時は None を返す）。
    - rank / factor_summary: ランク変換・各種統計量（count/mean/std/min/max/median）を提供。
  - research.__init__ で必要関数を公開。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX (Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。アクセス拒否等の例外は警告でスキップ。
    - set_cpu_affinity: 指定コア数に固定する機能（未指定は全コア使用）。エラーは警告でスキップ。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）／DB パス指定（--db）対応。
    - P95 計算、各種 SQL クエリ（system_status / trade_logs / risk_logs）からの集計、出力フォーマットを実装。

- AI ニュース NLP（部分実装）
  - ai.news_nlp:
    - raw_news を銘柄毎に集約し OpenAI (gpt-4o-mini) にバッチで送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む設計を導入。
    - バッチサイズ、文字数制限、最大記事数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ、部分成功時の DB 書き換え方式（該当コードのみDELETE→INSERT）等の処理方針を記載。
    - calc_news_window、API キー解決、定数設定、システムプロンプト等の基礎実装あり（ただしファイルの一部がスニペットで途切れているため完全な処理確認は未完）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env のパースに関する多くのエッジケース（引用符内エスケープ、export プレフィックス、コメント扱いなど）に対応し、環境設定読み込みの堅牢性を向上。

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得する設計。キー未設定時は明示的に ValueError を送出して処理を中断。

Known issues / Notes
- portfolio.position_sizing / risk_adjustment:
  - apply_sector_cap 内の価格欠損時の取り扱いに TODO コメントあり（price が 0.0 の場合、エクスポージャー過少見積りとなる可能性）。将来的にフォールバック価格（前日終値や取得原価）を導入する必要あり。
  - "unknown" セクターはセクター制限対象外としている点は設計上のトレードオフ（意図的）。
- utils.process_priority:
  - プロセス優先度設定はプラットフォーム依存で、権限不足や未対応 OS の場合は警告してスキップする実装。運用環境によっては効果が限定される可能性あり。
- run_monitoring:
  - MONITOR_POLL_INTERVAL に 0 以下または非整数を渡すと警告してデフォルトにフォールバックする挙動。意図しない短インターバル変更を防ぐための設計。
- ai.news_nlp:
  - 提供されたコードスニペットが途中で途切れているため、_fetch_articles 相当の実装および一連の DB 書き込み処理の完了・テストは未確認。OpenAI への API 呼び出しおよび JSON パース部分は多数のエラーハンドリングが記載されているが、実運用前に追加テスト推奨。
- DuckDB / SQLite 関連:
  - DuckDB への executemany 等でパラメータが空だとエラーとなるバージョン固有の注意点がコメント中にあり（処理前に params が空でないことを確認する実装方針）。

Contributing
- バグ報告・改善提案は issue を立ててください。特に以下を歓迎します:
  - news_nlp の完全実装・テスト・ロギング強化
  - position_sizing の価格フォールバック実装
  - DuckDB クエリのパフォーマンスチューニング

ライセンス
- 本リポジトリのライセンス情報はソース側で明示されていないため、配布前にライセンスファイルを追加してください。
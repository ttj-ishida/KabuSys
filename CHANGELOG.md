Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 基本アプリケーション初期実装を追加
  - パッケージバージョンを 0.1.0 として定義 (kabusys.__init__.py)。
- 実行/監視コマンドラインスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite DB を使用（データを本番と完全に分離）。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス開始時にプロセス優先度を "high" に設定。
    - DuckDB 接続を受け取り分析用 DB と連携。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度を "high" に設定して開始。
- 設定/環境管理
  - kabusys.config.Settings を実装
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。OS 環境変数を保護して .env.local/.env を読み込む。
    - 環境変数パースの堅牢化（コメント、export プレフィックス、クォート済み値のバックスラッシュエスケープ対応）。
    - 各種設定プロパティを提供（J-Quants/Kabu API、LINE、DuckDB/SQLite パス、paper trading、監視閾値、PID/KILL フラグ、ログレベル等）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等で不正値は例外）。
- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差異を吸収してプロセス優先度を設定する set_process_priority(level) を実装。
    - CPU アフィニティを固定する set_cpu_affinity(cpu_count) を実装。
    - アクセス権限や未対応 OS の場合は安全にフォールバックして警告出力。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選抜。
    - calc_equal_weights / calc_score_weights: 等金額／スコア加重配分（スコア全0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有を基に新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に基づく投下資金乗数。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap スケーリング、cost_buffer を考慮した保守的見積り、scale-down 後の端数処理（残差順に lot 単位で配分）。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、ATR/価格、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（財務データの最新レコード取得ロジックを含む）。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons の検証あり。
    - calc_ic: ファクター vs 将来リターンのスピアマン順位相関（IC）計算（必要レコード数 <3 の場合は None）。
    - rank / factor_summary: ランク変換、ファクター列の基本統計量（count/mean/std/min/max/median）。
  - research.__init__: zscore_normalize を外部（kabusys.data.stats）からエクスポートし、上記関数を公開。
- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news を銘柄別に集約して gpt-4o-mini（JSON モード）にバッチ送信しセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、最大記事数/文字数トリム、429/ネットワーク/5xx のための指数バックオフ・リトライを実装（最大リトライ回数等の定数化）。
    - レスポンスの厳密な JSON 検証、スコアのクリップ、部分失敗時の保護（対象コードのみ置換）を採用。
    - calc_news_window を提供（JST ベースの収集ウィンドウを UTC naive datetime に変換）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はソース内定数で管理）。
    - P95 計算、日付フィルタ、DB 存在チェック、エラーハンドリング（テーブルが無い場合のフォールバック）を実装。
- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの冪等初期化を実行（run_execution/run_monitoring で使用）。

Changed
- なし（初期実装のため）

Fixed
- なし（初期実装のため）

Security
- 環境変数ロード時に OS 環境（既存の環境変数）を保護する挙動を導入（.env の読み込みで既存値を勝手に上書きしない設計、.env.local は override=True だが protected により OS env は保護）。

Notes / Implementation details
- 多くの計算ロジックは「純粋関数」として設計されており、DB 参照を行う関数と純粋計算関数を明確に分離している（テスト容易性を考慮）。
- DuckDB は分析用に、SQLite は監視・実行の永続化用に使い分けられている。
- Paper Trading モードは本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- ログレベルや閾値、パス等は Settings 経由で環境変数から柔軟に設定可能。
- 将来的な拡張箇所（TODO コメントあり）
  - position_sizing の lot_size を銘柄別に持たせる拡張
  - apply_sector_cap の price 欠損時のフォールバック価格導入

作者注
- この CHANGELOG は提供されたコードベースの内容から推測して作成したものであり、リポジトリのコミット履歴を直接参照していません。実際のリリース履歴に合わせて日付・バージョンやカテゴリを調整してください。
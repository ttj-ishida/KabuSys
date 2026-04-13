CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に準拠しています。
通常のセマンティックバージョニングを採用します。

フォーマット
- 追加: 新規機能、エクスポート、CLI 等
- 変更: 既存機能の振る舞い変更やリファクタ
- 修正: バグ修正、例外処理やログ改善 等
- 注意: 動作上の重要な振る舞いや既知の制約

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本パッケージ初期版を追加
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や整数変換不能）はデフォルトにフォールバックし警告を出力。
    - 監視用途は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.Settings を実装
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。OS 環境変数は保護され上書きされない。
    - 柔軟な .env パーサ実装（export KEY=val, 引用符・エスケープ、インラインコメントの扱いなどを考慮）。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / paper_trading 用 DB / 監視閾値 / PID/KILL フラグ等）とバリデーションを提供。
    - PAPER_FILL_MODE 等の有効値チェックを実装。
- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils.process_priority.set_process_priority / set_cpu_affinity
    - Windows と POSIX（Linux, Darwin, FreeBSD）を吸収する実装。
    - 権限不足や未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順、signal_rank によるタイブレークで候補を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャで上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に対する投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3、未知は 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算、単元株丸め、per-stock 上限、aggregate cap（available_cash を超える場合はスケーリング）を実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的見積もり、残差処理で lot 単位の追加配分ロジックを実装。
- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value を提供。prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - ウィンドウ不足時の None ハンドリングを明記。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算、horizons のバリデーションあり。
    - calc_ic / rank / factor_summary: IC（Spearman ランク相関）計算、ランク付け（同順位は平均ランク）、ファクター統計要約を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ をエクスポート。
- AI ニュース NLP（OpenAI 経由のセンチメント）
  - ai.news_nlp
    - raw_news と news_symbols を集約し、gpt-4o-mini を用いて銘柄ごとのセンチメントスコアを ai_scores テーブルに書き込む処理を実装。
    - target_date に基づくニュースウィンドウ計算（JST で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（デフォルト 20 銘柄/回）、最大記事数と文字数のトリム、429/ネットワーク/5xx 等のエクスポネンシャルバックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ等を実装。
    - API キーが未設定の場合は明示的な ValueError。
    - 部分失敗時に既存スコアを守るため、更新は対象コードのみで置換（DELETE/INSERT の限定的適用）。
- CLI ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を SQLite (paper_trading.db デフォルト) から集計し、PASS/FAIL 判定を出力する。
    - P95 の計算、範囲フィルタ (--from/--to)、DB 存在チェック、テーブル欠損時のフォールバックを実装。

Changed
- n/a（初回リリースのため既存変更なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Notes / Known limitations
- Settings の自動 .env ロードはプロジェクトルートが検出できない場合にスキップされる。そのため配布パッケージ環境では .env 自動ロードを期待しないでください。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。
- process_priority の優先度設定は OS 権限に依存し、権限不足時は警告を出してスキップする（安全設計）。
- position_sizing は現状 lot_size を全銘柄共通で扱う。将来的に銘柄別 lot_map への拡張を想定している旨をコメントで記載。
- research, ai モジュールは DuckDB / OpenAI API に依存するため、実行環境に適切なデータと API キーが必要。
- news_nlp は外部 API（OpenAI）へのコールを伴うため、API 利用制限やコストに注意。レスポンスの堅牢性確保のため複数のリトライ・バリデーションを実装しているが、完全な成功保証はない。

Authors
- このリリースはコードベースの実装内容に基づき CHANGELOG を作成しました（コード内 docstring / 実装より推測）。

---

この CHANGELOG はコード内のドキュメントや docstring を元に推測して作成しています。必要に応じて日付、バージョン、詳細を調整してください。
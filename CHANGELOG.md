Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

注: 以下の変更点は与えられたコードベースから推測して記載しています。実際の変更履歴とは差異がある可能性があります。

Unreleased
----------

### Added
- News NLP モジュールを追加（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装。
  - 銘柄ごとに記事を集約して最大 20 銘柄ずつバッチ送信、API レスポンスの検証、スコアを ±1.0 にクリップして ai_scores テーブルへ書き込み。
  - 429/ネットワーク/5xx などに対するエクスポネンシャルバックオフのリトライを実装。
  - ニュース収集ウィンドウ（JST 基準）算出ユーティリティを提供。
  - 注意: 実装ファイルが途中で切れている箇所があり（コード断片の末尾）、一部処理が未完または追加のエラーハンドリング・書き込み処理が必要。

### Changed
- なし（新規機能の追加が中心のため）

### Fixed
- なし（推測ベースの記載）

0.1.0 - 2026-04-17
------------------

初回リリース。以下の主要機能・モジュールを含む。

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - export 形式やクォート、インラインコメントの取り扱いに対応した .env パーサーを実装。
  - OS 環境変数は保護（既存の OS 環境変数を上書きしない挙動）し、KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを実装し、各種環境変数（J-Quants/LINE/Kabu API、DB パス、監視閾値、環境モード等）をプロパティで取得。入力値バリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行系ランチャー
  - run_execution.py
    - プロセス優先度を高く設定してから起動（utils/process_priority.set_process_priority を利用）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを作成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止機構を実装。
    - ExecutionEngine 起動時に pid ファイルを書き込む仕組み（pid_path を指定）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でループ間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告ログを出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは一元化）。
    - stop flag 検知および KeyboardInterrupt による正常終了処理を実装。

- 監視 DB 初期化（kabusys.monitoring.monitoring_db）
  - run_* スクリプトから呼び出される DB 初期化処理を用意（テーブル存在保証、冪等性）。

- Execution 関連コンポーネント
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine（起動/停止/セッション実行）を統合する基盤を追加。
  - RiskManager のデフォルト設定値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() から初期化。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位 N 選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は等配分にフォールバックして警告ログ出力。
  - risk_adjustment
    - apply_sector_cap: セクター集中を防ぐための候補フィルタ（売却予定コードの除外・unknown セクターは上限を適用しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap によるスケールダウン、余剰分の lot 単位での再配分を実装。
    - cost_buffer による手数料/スリッページ考慮。

- 研究（research）モジュール（kabusys.research）
  - factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いたファクター計算（prices_daily / raw_financials テーブル参照）。ウィンドウ不足時は None を返す安全設計。
  - feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一クエリで取得。horizons の入力検証あり。
    - calc_ic: スピアマンのランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary, rank: 基本的な統計要約・ランク計算。ties は平均ランクで処理。

- データ処理ユーティリティ
  - DuckDB を用いる想定の SQL ベース計算を多用（research / ai / tools モジュール）。
  - zscore_normalize を外部データ.stats からエクスポート（kabusys.research.__init__）。

- ツール（kabusys.tools）
  - paper_verification_report
    - Paper Trading の検証レポート自動生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し PASS/FAIL を判定する。閾値はソース内定義（稼働率 99% など）。
    - コマンドライン引数で期間指定（--from/--to）と DB パス指定（--db）に対応。
    - DB が存在しない場合はわかりやすいエラーメッセージを出力。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows/POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出力してスキップ。
  - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を固定するユーティリティ。引数検証と例外ハンドリングあり。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサー強化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理するよう実装。
  - 無効行や空行、コメント行をスキップ。

### Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出して誤ったキー使用を防止。

Notes / Implementation details
------------------------------
- 多くの関数は外部副作用を持たない純粋関数として設計（特に portfolio/*）。ユニットテストが書きやすい構造。
- DuckDB を解析/集計基盤として利用する設計（高速な列指向集計を想定）。
- Paper Trading 環境は本番と DB を分離して安全にテスト可能に設計。
- エラーハンドリングは基本的に fail-safe（API エラーや DB の一部欠損があっても他処理を継続する意図の実装多数）。
- news_nlp モジュールは強力な機能を備える一方で、提示したコードでは途中で切れている箇所があるため、本番運用前に未完箇所の実装と追加の統合テストが必要。

Contributing
------------
改訂やバグ修正を行う場合は、各モジュールの責務（純粋関数／副作用あり処理）を尊重して変更を行ってください。特に以下に注意してください:
- 環境変数の自動ロード挙動を変える場合はテスト環境への影響を考慮する（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- Paper Trading 用 DB と本番 DB の分離ポリシーを維持すること。
- OpenAI 利用部はレート制限・API コストに注意し、リトライ・バックオフのパラメータを調整すること。

（以上）
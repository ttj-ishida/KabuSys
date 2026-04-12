CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このファイルはコードベースの内容から推測して作成しています。

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-04-12
-----------------

Added
- 基本リリース: KabuSys v0.1.0
  - 日本株自動売買システムのコア機能群を提供する初期版リリース。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、MockBrokerClient を経由して完全に本番 DB と分離して実行する設計。
    - 起動時にプロセス優先度を "high" に設定するフローを追加。
    - init_monitoring_db を呼び出して監視テーブルの存在を保障。
    - duckdb 接続を受け取り、ExecutionEngine を構成してセッション実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（モニタリング専用の挙動）。
    - 例外発生時もループを継続するフェイルセーフ実装（check_once() 内例外はログ出力して次ポーリングへ）。
- 設定管理
  - config.Settings を導入し、.env / .env.local / OS 環境変数からの設定読み込みロジックを提供。
    - プロジェクトルート検出（.git または pyproject.toml を基準）によりカレントディレクトリ依存を排除。
    - .env の行パーサーは export プレフィックス・クォート（シングル/ダブル）・バックスラッシュエスケープ・インラインコメント処理などに対応。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 多数の設定プロパティを追加（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/kill flag / 環境判定等）。
    - 環境変数値のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクター集中を検出して新規候補から除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応し、銘柄ごとの発注株数を計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、余剰キャッシュを用いた再配分ロジックを実装。
    - cost_buffer を用いた保守的コスト見積りに対応。
- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照し、モメンタム・ボラティリティ・バリュー系ファクターを DuckDB SQL で効率的に計算。
    - 各関数は必要データ不足時に None を返す等の安全な挙動を実装。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons の検証（正の整数かつ <= 252）あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: ランク処理（同順位は平均ランク）と基本統計量集計を提供。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize をデータ統計ユーティリティとしてエクスポート。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ・トークン肥大化対策（最大記事数・最大文字数）、JSON Mode 出力検証、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）をサポート。
    - ニュース収集ウィンドウ計算関数 calc_news_window を提供（JST ルールに基づく UTC 変換）。
    - API キー未設定時は明示的に ValueError を送出。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定を提供。未対応 OS は警告してスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスを固定する機能を提供。アクセス権限や未実装例を捕捉して警告を出すフェイルセーフ。
    - これらは実行スクリプトの起動直後に使用されることで安定稼働を支援。
- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプト（CLI）。日付フィルタ (--from/--to)、DB パス指定（--db / 環境変数）に対応。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の集計と PASS/FAIL 判定基準を実装。
    - DB 閉塞やテーブル欠損に対して例外を吸収して N/A や 0 を返す堅牢な実装。
- パッケージ情報
  - __init__.py にて __version__="0.1.0" を設定。

Changed
- 設計方針の明確化
  - research や portfolio の多くの関数は副作用を持たない純粋関数として設計され、DB 参照や外部 API 呼び出しを分離（安全性・テスト容易性を向上）。
  - Execution / Monitoring の DB 初期化（init_monitoring_db）を起動フロー内で保証することで冪等性を担保。

Fixed / Robustness improvements
- .env パーサーの堅牢化
  - export プレフィックス、クォート文字・エスケープ、インラインコメントの扱いなどを改善し、一般的な .env の記述に対応。
- 環境変数検証
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE に対する検証を追加し、不正値時は ValueError を送出することで不整合を早期に検出。
- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL が不正または 0 以下の場合はデフォルト（60 秒）にフォールバックし、time.sleep に渡せる安全な値を保証。
  - SystemMonitor.check_once() 内で例外が発生してもループ継続するように try/except を配置。
- SQL クエリ・集計の安全性
  - factor / volatility / forward returns 等の SQL 実装でデータ不足時に None を返す等、NULL の伝播・カウント処理に注意した実装を行い予期せぬ例外を抑制。
- P95 計算
  - 空リストの場合は None を返すようにして呼び出し側で安全に扱えるようにした。

Security
- OpenAI API キーの扱いは引数または環境変数を明示的に要求し、未設定時はエラーを出すことで誤操作を防止。

Notes / Known limitations
- ai.news_nlp と一部の機能は外部 API（OpenAI）や DuckDB に依存しており、実行環境でのキー設定や DB 構築が前提。
- position_sizing の lot_size は現状グローバル固定（将来的には銘柄別 lot_map へ拡張予定）。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーを過小見積りする可能性があり、将来的にフォールバック価格の採用を検討。
- 一部ファイルの実装（ai.news_nlp の最後の一部処理）はこのスナップショットでは途切れているため、完全なバッチ書き込み・部分失敗時のロールバック戦略はコード全体での検証が必要。

Authors
- この CHANGELOG は提供されたコードベースからの推測に基づいて作成しています。実際のコミット履歴や変更履歴がある場合はそれに合わせて更新してください。
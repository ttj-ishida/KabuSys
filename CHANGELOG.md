KEEP A CHANGELOG — 変更履歴
==========================

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。
改版番号はセマンティックバージョニングに従います。

[Unreleased]
------------

- （未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージ情報:
    - kabusys のパッケージメタ情報を追加（__version__ = 0.1.0）。
  - 設定管理:
    - 環境変数/.env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パーサーは export プレフィックス、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの取り扱いをサポート。
    - OS 環境変数を保護する override / protected ロジックを実装。
    - Settings クラスを提供し、各種設定（DB パス、PID パス、監視しきい値、PAPER_FILL_MODE 等）をプロパティ経由で取得可能に。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL 等のバリデーションを実装。

- 実行用スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - paper_trading 環境時には MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - DuckDB / SQLite 接続の初期化・クローズ処理を実装。
    - OrderRepository、OrderManager、RiskManager（RiskConfig を含む）、Reconciler、ExecutionEngine の組み立てと実行フローを定義。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視機能は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を "high" に設定し、例外発生時もループ継続するフェイルセーフな実行。

- 監視・ツール:
  - monitoring_db 初期化呼び出しを実装（冪等に監視テーブルを作成）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 日付フィルタ (--from/--to)、--db オプション、PAPER_TRADING_SQLITE_PATH に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標集計および PASS/FAIL 判定（閾値はソースに定義）を出力。
    - P95 計算、欠損データ時の安全ハンドリング、DB 存在チェックを実装。

- ポートフォリオ構築（純粋関数群）:
  - portfolio_builder.py
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合はフォールバック）を実装。
  - risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を考慮したセクター別エクスポージャー計算）を実装。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知のレジームは警告と 1.0 フォールバック）。
  - position_sizing.py
    - position size 計算を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer を導入し手数料・スリッページを保守的に見積もり、スケーリング時に残差を lot 単位で再配分するロジックを実装。
    - 不足価格データや価格 <= 0 のハンドリングを実施。

- リサーチ / ファクター計算:
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - MA200、ATR20、20日平均売買代金、各ホライズンのリターン等を SQL ウィンドウ関数で計算し、データ不足時は None を返す設計。
    - 計算はメモリ内の DuckDB 経由でサーバー外 API に依存しない純粋な実装。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）を実装。
    - スピアマンランク相関（IC）を計算する calc_ic、rank、factor_summary（count/mean/std/min/max/median）などの統計ユーティリティを実装。
    - pandas 等の外部ライブラリに依存しない実装。

- AI / ニュース NLP:
  - ai/news_nlp.py
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）を用いたセンチメントスコアリングを実装。
    - 扱い:
      - タイムウィンドウ（JST ベース → UTC 変換）を明確化し、ルックアヘッドバイアスを防止（datetime.today() を参照しない）。
      - 1 銘柄あたり記事数・文字数の上限設定（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
      - バッチ処理（最大 20 銘柄/コール）、JSON mode で結果検証。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ。
      - スコアを ±1.0 にクリップし、部分失敗時に既存スコアを保護するため該当銘柄のみ置換（DELETE→INSERT の絞り込み）。
    - OpenAI クライアントは OpenAI パッケージを利用。API キーは引数または環境変数 OPENAI_API_KEY から取得。

- ユーティリティ:
  - utils/process_priority.py
    - プラットフォーム抽象化されたプロセス優先度設定（Windows: 高・通常・低 を専用定数で、POSIX: nice 値で実装）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対しては警告ログを出してスキップするフェイルセーフを実装。

- パッケージ API エクスポート:
  - portfolio と research モジュールの主要関数を __all__ で公開。

Changed
- 初期実装のため特記事項なし（初回リリース）。
  - 設計上の注記として、いくつかの関数は将来的な拡張（銘柄別 lot_size、価格フォールバック戦略など）を想定していることを README/ソース内の TODO コメントで明示。

Fixed
- 初回リリースのため特記事項なし。

Notes / Implementation highlights
- 設計方針:
  - リサーチ/ポートフォリオ関連は副作用を持たない純粋関数で実装し、テスト容易性と予測可能性を重視。
  - 本番 API（kabu API 等）および取引所とのやり取りは execution 層に集約。research/ai は読み取り専用（DB 経由）で発注には関与しない。
  - フェイルセーフを重視。外部依存（OpenAI、psutil など）で失敗してもサービス全体が停止しない設計。
- 依存ライブラリの例:
  - duckdb, psutil, openai（実行環境で必要）。

今後の予定（例）
- 単体テストの追加（特に position sizing / aggregate scaling の境界ケース）。
- 銘柄別単元（lot_size）対応の導入。
- price の欠損時フォールバック（前日終値や取得原価）を実装してエクスポージャー計算精度を改善。
- ai/news_nlp の出力検証を強化し、より詳細なログ・監査トレイルを追加。

--- 

（この CHANGELOG.md は現在のコードベースから推測可能な変更点・機能をまとめたものです。実際のコミット履歴やリリースノートが存在する場合はそちらに合わせて調整してください。）
保持する形式: Keep a Changelog 準拠

全体概要
========
この CHANGELOG は、コードベースから推測できる主要な変更点・機能追加をまとめたものです。
バージョンや日付はコード内の手がかりおよび現日時点の推測に基づいています。

Unreleased
----------
（現在のブランチでまだリリースされていない変更があればここに記載します。）
- （無し）

0.1.0 - 2026-04-16
-----------------
Added
- 基本パッケージ情報を追加
  - kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - ストップフラグ (data/stop_requested.flag) 検知時の安全な停止ロジックを実装。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう明示。
    - 停止フラグ検知でループを終了する安全処理、例外時のログ保持と継続処理を実装。

- 設定管理
  - kabusys/config.py: Settings クラスと .env 自動読み込み機能を実装。
    - プロジェクトルート判定（.git または pyproject.toml）に基づく自動 .env/.env.local の読み込み。
    - .env のパース機能強化: export プレフィックス対応、クォート・エスケープ処理、インラインコメントの取り扱い。
    - 環境変数の保護（OS 環境変数を上書きしない挙動）をサポート。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、paper_trading のパス・挙動など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。

- Portfolio 構築ライブラリ
  - kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等配分にフォールバックして警告を出す挙動を追加。
  - kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を実装 (apply_sector_cap)。既存保有のセクター比率が上限を超える場合、新規候補を除外。
    - unknown セクター扱いの説明と除外しない方針。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装。既知レジーム (bull/neutral/bear) をマップし、未知レジームは警告とともにフォールバック 1.0。
  - kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の各方式）。
    - 単元株（lot_size）で丸め、per-stock と aggregate のキャップを考慮したスケーリングと残差分配ロジックを実装。
    - 価格欠損時のスキップやログ出力により安全に動作。

- Research / ファクター計算
  - kabusys/research/factor_research.py
    - Momentum, Volatility, Value など複数ファクター計算を実装。DuckDB 上の prices_daily / raw_financials を利用する SQL ベース実装。
    - 各関数は date, code をキーとした辞書リストを返却する純粋関数設計。
  - kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク付けユーティリティ (rank) を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。ties の取り扱いや丸めに配慮した実装。

- ツール
  - kabusys/tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成ツールを追加（CLI）。
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - P95 や集計クエリ、期間フィルタ、閾値（デフォルト）を指定。DB の存在チェックや OperationalError に対するフォールバックを備える。

- AI / ニュース NLP
  - kabusys/ai/news_nlp.py
    - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、記事トリム（最大記事数・文字数）、バッチ送信、429/5xx/タイムアウトに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（書換対象コードの限定）などの設計思想を盛り込む。
    - （ファイル末尾で処理が途中で切れているように見えますが、主要な設計と定数は実装済み。）

- ユーティリティ
  - kabusys/utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを実装（Windows / POSIX 対応）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応プラットフォーム時は警告でスキップする安全実装。
  - その他パッケージ初期化ファイル等を追加（kabusys/tools/__init__.py, kabusys/utils/__init__.py 等）。

Changed
- 設定の読み込み挙動を明示化
  - .env → .env.local の読み込み順（.env を先に読み、.env.local で上書き）が導入され、OS 環境変数は保護される。
- 実行時のプロセス優先度設定が起動初期に行われるよう統一（run_execution と run_monitoring で set_process_priority("high") を実行）。

Fixed / Robustness
- 環境変数パースの強化により、クォートやバックスラッシュエスケープ、export プレフィックス、インラインコメントの誤解釈などの問題を軽減。
- MONITOR_POLL_INTERVAL が不正値の際にデフォルトにフォールバックしてログ出力するようにして、time.sleep での ValueError を回避。
- position_sizing / calc_score_weights で全スコアが 0 の場合に等配分へフォールバックして不正なゼロ除算を防止。
- DuckDB / SQLite のクエリ処理において、テーブルが存在しない場合の sqlite3.OperationalError を捕捉してフォールバックする処理を tools/paper_verification_report に実装。

Notes / その他
- Paper Trading 環境を明確に分離しており、テスト・検証時に実口座データに触れない設計になっている（設定: KABUSYS_ENV=paper_trading）。
- 多くのモジュールは外部副作用を持たない純粋関数（portfolio や research 系）として設計されているためユニットテストが容易。
- ai/news_nlp.py は詳細な API リトライ設計や出力検証を備えているが、コードの末尾が切れているため完全な書き込み処理の実装は要確認。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で指定する必要がある旨をチェックし、未設定時は ValueError を発生させる。

今後の改善提案（コードからの推測）
- ai/news_nlp の残りの実装を完了し、外部 API 呼び出し部分の単体テスト（モック化）を追加する。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）を実装してブロック解除の誤判定を防ぐ（TODO コメントあり）。
- duckdb.executemany 周りの互換性チェック（実行前に params が空でないことを保障する処理など）をリファクタリングして安定性向上。
- ロギング構成（ログレベル・出力先）を Settings.log_level に合わせて統一的に初期化する仕組みを整備。

ライセンス
- 本 CHANGELOG はコードの内容から推測して作成されています。実際のコミットログ・リリースノートと相違がある可能性があります。
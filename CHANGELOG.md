CHANGELOG
=========

すべての重要な変更履歴を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開: KabuSys パッケージの基盤機能を実装。
  - 基本情報
    - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。
  - 環境設定
    - src/kabusys/config.py
      - .env ファイルの自動読み込み機構（プロジェクトルート探索: .git / pyproject.toml を基準）。
      - .env パーサーを実装（export 形式、クォート、インラインコメント対応、保護された OS 環境変数の扱い）。
      - Settings クラスを実装し、J-Quants / kabu API / LINE / DB /監視閾値 / システム設定等のプロパティを提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
      - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証を実装。
  - 実行用スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動。
      - 起動時にプロセス優先度を "high" に設定。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は環境にかかわらず本番 sqlite_path を使用して稼働状況を記録する設計。
      - 起動時にプロセス優先度を "high" に設定。
  - 監視 DB 初期化
    - init_monitoring_db 呼び出しを run_execution/run_monitoring の起動時に行い、監視テーブルの存在を冪等に保証。
  - プロセス制御ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX の差分を吸収してプロセス優先度 (high/normal/low) を設定。
      - CPU affinity 設定ユーティリティ set_cpu_affinity を提供（core 数指定でプロセスを最初の N コアに固定）。
      - 権限不足や未対応 OS はワーニングでスキップ。
  - ポートフォリオ構築
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
      - スコア全て 0 の場合は等金額配分へフォールバック（警告ログ）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限の適用（apply_sector_cap）。
      - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既知レジーム: bull/neutral/bear（未知はフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数計算（calc_position_sizes）を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash でスケールダウン）、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。
  - 研究（Research）モジュール
    - src/kabusys/research/factor_research.py
      - モメンタム / ボラティリティ / バリュー各ファクター計算を DuckDB 上の SQL で実装。
      - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials テーブル参照）。
      - 長期移動平均や ATR 等のウィンドウサイズと不足時の None 扱いの方針を明記。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、rank（平均ランク tie 処理付き）、ファクター統計サマリー（factor_summary）を実装。
      - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py
      - 主要な研究用 API をエクスポート（zscore_normalize を含む）。
  - AI / ニュース NLP
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
      - バッチサイズ・トークン肥大化対策（記事数・文字数上限）、タイムウィンドウ（JST基準の前日15:00〜当日08:30をUTCに変換）を仕様化。
      - API レベルでのリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで行う方針、JSON レスポンスの厳密検証、スコアを ±1.0 にクリップ。
      - OpenAI API キー未設定時は明示的なエラーを返す（api_key 引数または OPENAI_API_KEY 環境変数を使用）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート出力ツールを実装（コマンドライン実行可能）。
      - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など。
      - 判定閾値（稼働率 >= 99% 等）を定義し、PASS / FAIL 判定を表示。
      - DB パスは --db / 環境変数 / デフォルト の順で解決。
  - モジュールパッケージング
    - 各モジュールをパッケージとしてエクスポートするための __init__ 実装（portfolio, research, utils, tools 等）。

Changed
- 設計上の明確化:
  - Paper Trading は実際の注文の検証用であり、DB・動作を本番と完全分離する方針を明記（run_execution）。
  - 監視処理は常に本番の sqlite_path を参照して稼働状況を追跡する方針を明記（run_monitoring）。
  - Research / AI / Portfolio の関数は副作用を持たない純粋関数を基本とし、DB 参照が必要な部分は明示的に接続を受け取る設計。
- 環境変数パースの堅牢化:
  - export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント取り扱いをサポート。
  - 自動読み込み時に OS の環境変数を protected として扱い、明示的に override 可能な挙動を実装。

Fixed
- 設定値の検証追加 / 想定外値時のフォールバック:
  - MONITOR_POLL_INTERVAL: 0 以下や不正値はログで警告しデフォルト (60 秒) にフォールバック（run_monitoring）。
  - PAPER_FILL_MODE: 無効値の検出と ValueError を追加（Settings.paper_fill_mode）。
  - KABUSYS_ENV / LOG_LEVEL: 不正値に対して ValueError を送出するバリデーション実装。
- DuckDB executemany の制約に配慮した実装注記（ai/news_nlp の書き込み処理で params が空でないことを確認）。

Security
- 特になし。

Notes / ユーザー向け情報
- 環境変数（主要）
  - KABUSYS_ENV: development | paper_trading | live（必須ではないが有効値のみ許可）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。0 以下・不正値は 60 にフォールバック。
  - PAPER_FILL_MODE: paper_trading 時の MockBroker の挙動。instant | partial | never | reject（デフォルト: instant）。
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）。
  - SQLITE_PATH / DUCKDB_PATH: それぞれのデフォルトは data/monitoring.db, data/kabusys.duckdb。
  - OPENAI_API_KEY: AI ニューススコアリングを使用する場合は必須。
- 実行方法
  - 監視ループ: python -m kabusys.run_monitoring （MONITOR_POLL_INTERVAL により間隔変更可）
  - 実行エンジン: python -m kabusys.run_execution （KABUSYS_ENV により paper_trading 動作切替）
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実装上の注意
  - 多くの関数は DuckDB / SQLite 接続を引数として受ける設計であり、テストしやすく副作用が限定されています。
  - position_sizing では現状 lot_size は全銘柄共通のパラメータ。将来的に銘柄別単元拡張を計画中（TODO コメントあり）。
  - 一部モジュール（AI スコアリングの続きを含む処理フロー）は堅牢なエラーハンドリングや部分更新ロジックを備えていますが、運用前に API キー設定や DB スキーマ整備を確認してください。

将来の予定（案）
- 銘柄別の lot_size マスタ導入および position_sizing の拡張。
- price の欠損時の価格フォールバック（前日終値・取得原価など）導入によるエクスポージャー計算改善。
- AI スコアリングのテストケース・レスポンス検証強化。
- DuckDB / SQLite スキーマ定義のドキュメント化とマイグレーション仕組みの追加。

---
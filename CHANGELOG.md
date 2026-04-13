# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このリポジトリの初期リリースはバージョン 0.1.0 として記録しています。以下は、ソースコードから推測できる機能追加・設計・既知の注意点の要約です。

全般
- バージョン: 0.1.0
- リリース日: 2026-04-13

## [0.1.0] - 2026-04-13

### Added
- 基本アーキテクチャと主要コンポーネントを実装
  - パッケージ名: kabusys
  - バージョン情報: src/kabusys/__init__.py にて `__version__ = "0.1.0"`

- 実行エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視用 DB（SQLite）と DuckDB を接続して使用。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
    - KeyboardInterrupt による正常終了処理と DB 接続のクローズを実装。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は paper 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成（paper_trading 時は MockBrokerClient が使われる想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て ExecutionEngine を run_session() で起動。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - src/kabusys/config.py: Settings クラスを実装
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサは export プレフィクス、クォート（シングル/ダブル）のエスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - デフォルト DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db、PAPER_TRADING_SQLITE_PATH= data/paper_trading.db。

- モジュール: portfolio
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア重みの算出（スコア全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタリング。sell_codes を除外して計算。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返却（未知値は 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap スケーリング、cost_buffer による保守的見積り、残差に基づく追加配分ロジックを実装。

- 研究・分析モジュール（research）
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照してファクターを計算。
    - 各値の欠損/データ不足時の取り扱い（必要行数未満は None）。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21営業日）を計算。
    - calc_ic: スピアマンランク相関（IC）計算。有効レコードが 3 未満の場合は None を返す。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ。
  - 実装方針: DuckDB を直接用い、pandas 等の外部ライブラリに依存しない純粋 Python + SQL 実装。

- AI ニュース NLP（ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）に送信して銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
  - ニュース取得ウィンドウ（JST 基準で前日 15:00 〜 当日 08:30）を計算する calc_news_window 実装。
  - バッチサイズ、記事数上限、文字数上限、スコアクリップ、リトライ（指数バックオフ）等の実装方針あり。
  - API キー未設定時は ValueError を送出する。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows と POSIX（Linux, Darwin, FreeBSD）での差分を吸収。
    - psutil の権限不足等は警告ログでスキップするフェイルセーフあり。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB を読み、稼働率・注文成功率・送信率・レイテンシ等の検証レポートを CLI 出力。
    - P95 計算、閾値（稼働率 99% 等）による PASS/FAIL 判定。
    - コマンドライン引数: --from / --to / --db をサポート。

- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは明示的に指定する（引数または環境変数 OPENAI_API_KEY）。未設定時は処理を中断しエラーを返す設計。

### Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性あり。将来的には前日終値や取得原価へのフォールバックを検討する旨の TODO コメントあり。
- position_sizing.calc_position_sizes:
  - 現状 lot_size は全銘柄共通の引数で扱われる（将来的に銘柄別 lot_size を stocks マスタで扱う拡張を想定）。
- ai/news_nlp.py:
  - 実運用での堅牢性（API レスポンスの厳密なバリデーション、部分失敗時の DB 保護など）が設計されているが、実装の続き（ファイル末尾で切れている部分）に注意が必要。
- .env パーサは多くのケース（クォート、エスケープ、export、インラインコメント）に対応しているが、特殊なケースは検証が必要。

---

（参考）変更ログの書式について
- 本ファイルは Keep a Changelog のカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security, Other）に概ね従って作成されています。今後の変更は Unreleased セクションを追加して段階的に記録してください。
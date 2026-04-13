CHANGELOG
=========

すべての注目すべき変更履歴を記載します。フォーマットは「Keep a Changelog」準拠です。

Unreleased
---------

- なし

0.1.0 — 2026-04-13
------------------

初回リリース。本プロジェクトは日本株自動売買システム "KabuSys" のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、リサーチ/ファクター計算、ニュース NLP スコアリング、ツール類を含みます。

Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 実行・監視スクリプト
  - run_execution.py を追加。ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine.run_session() によるセッション実行。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を利用）。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL により上書き可能（不正値はログを出してデフォルトへフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境
  - config.Settings を追加。環境変数ベースの設定取得用プロパティを多数実装。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグパス、しきい値（CPU/MEM/DISK）などを提供。
    - KABUSYS_ENV, LOG_LEVEL の検証を実装（許容値チェック、無効値は ValueError）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）。
  - .env ファイル自動ロード機能を実装
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定。
    - 読み込み順序: OS環境 > .env.local（上書き） > .env（未設定キーのみセット）。
    - OS 環境変数の上書きを防ぐ protected 機構を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースはクォート、エスケープ、インラインコメント等に対応。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナル選別 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - risk_adjustment: セクター上限適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を追加。
    - セクター上限を超過しているセクターの候補を除外するロジックを実装（"unknown" セクターは除外対象外）。
    - レジーム multiplier は bull/neutral/bear を実装し、未知のレジームは警告ログを出して 1.0 にフォールバック。
  - position_sizing: 株数計算ロジック (calc_position_sizes) を追加。
    - allocation_method に応じた計算 ("risk_based", "equal", "score")、lot_size による丸め、単銘柄上限・総投下上限・コストバッファによるスケールダウン、残余配分アルゴリズムを実装。
- ユーティリティ
  - utils.process_priority: set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収した上で優先度設定を行う。権限不足等はログで警告してスキップ。
- リサーチ / ファクター計算（research）
  - factor_research: momentum / volatility / value 各ファクター計算関数を追加（DuckDB 接続を受け SQL で実行）。
    - mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe などを算出。
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、rank、factor_summary を追加。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備し、zscore_normalize を外部モジュールから公開。
- AI / ニュース
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）で解析して ai_scores に書き込む処理を追加。
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）の計算、銘柄ごとの記事集約、1チャンク最大 20 銘柄のバッチ送信を実装。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、429/タイムアウト/5xx に対する指数バックオフによるリトライを実装。
    - API キーは引数か環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - コマンドライン引数 --from/--to/--db をサポート。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL を判定する閾値を定義（デフォルト閾値をソース中に明記）。
    - DB が存在しない場合のエラーメッセージを実装。
    - DuckDB や sqlite のテーブルが存在しない場合でも安全にフォールバックして N/A を出力する実装。

Changed
- 環境変数読み込みの挙動
  - .env/.env.local の自動ロードを導入し、OS 環境変数が優先されるよう変更（OS 環境を保護する protected 機構を採用）。
- モニタリングの DB 接続
  - run_monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様を明確化（モニタリングデータは本番 DB に一元化される設計）。
- 実行エンジンの DB 選択
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離するように変更。
- ログ出力レベルの初期化
  - 起動スクリプトで logging.basicConfig(level=logging.INFO) を設定して起動ログを安定化。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するよう改善。
- MONITOR_POLL_INTERVAL の扱い
  - 環境変数の不正（0・マイナス・非整数）を検知して警告ログを出し、デフォルト 60 秒にフォールバックするように変更（time.sleep に渡す不正値による例外を防止）。
- DuckDB executemany 対応留意
  - ai.news_nlp の説明コメントに DuckDB 0.10 の executemany の制約を考慮する旨を明記（部分失敗時に既存データ保護する挙動を採用）。

Security
- OpenAI API キーの取り扱い
  - api_key が明示されない場合は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError による明示的な失敗とすることで誤ったキー抜けを早期検出。

Notes / その他
- 多くの関数は「DB を直接更新しない」「純粋関数」「DuckDB/SQLite の接続を外部から受ける」設計方針に従って実装されています。ユニットテストが容易な設計です。
- 将来の拡張点（TODO コメント）
  - position_sizing: 銘柄別 lot_size を持つ拡張（stocks マスタを想定）。
  - apply_sector_cap: price 欠損時のフォールバック価格導入の検討。

ライセンス
- （該当するライセンス情報がプロジェクトに含まれている場合はそちらを参照してください。）

以上。変更内容の詳細や追加要望があれば教えてください。
CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 堅牢化
- Removed / Deprecated: 廃止・非推奨（該当なしなら省略）

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 実行 / 監視ランナー
    - run_execution.py
      - ExecutionEngine を起動するためのエントリポイント。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、別スレッドで engine.run_session を実行。
      - 停止フラグ (data/stop_requested.flag) による安全停止処理、実行中 PID ファイル管理、DB を finally で確実にクローズ。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動用スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可（デフォルト 60 秒）。
      - 監視用 DB 初期化（init_monitoring_db）、DuckDB 接続、プロセス優先度設定。
      - 停止フラグ検知でループ停止、例外はログ出力して次ループへフォールバック。
  - 設定 / 環境変数管理
    - config.py
      - Settings クラスを提供し、環境変数から各種設定を取得（DB パス、Paper Trading 設定、しきい値、ログレベルなど）。
      - .env 自動ロード（プロジェクトルートの検出: .git または pyproject.toml を基準）、.env/.env.local の読み込み順制御、OS 環境変数の保護機能。
      - .env パーサーは export 形式、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
      - 設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - ポートフォリオ構築ライブラリ
    - kabusys.portfolio
      - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分へフォールバック）。
      - position_sizing.py: calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮）。
      - risk_adjustment.py: apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（market regime に応じた投下資金乗数）。
  - リサーチ / ファクター計算
    - kabusys.research
      - factor_research.py: calc_momentum, calc_volatility, calc_value（DuckDB の prices_daily / raw_financials を利用して各種ファクターを計算）。
      - feature_exploration.py: calc_forward_returns（任意ホライズン）、calc_ic（スピアマンランク相関による IC）、factor_summary、rank（同順位は平均ランク）。
      - research/__init__.py で zscore_normalize 等と合わせてエクスポート。
  - AI ニュース NLP
    - ai/news_nlp.py
      - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装（バッチサイズ、文字数制限、タイムウィンドウ計算、API リトライ、レスポンス検証、スコアクリップなど）。
      - calc_news_window, score_news 等のユーティリティを含む。API キー未設定時は ValueError を送出。
  - ユーティリティ
    - utils/process_priority.py
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収し、権限不足や未サポート環境ではワーニングを出してスキップする設計。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。CLI オプションで期間指定 (--from, --to, --db) が可能。
      - 指標: 稼働率（uptime）、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等。閾値による PASS/FAIL 判定を出力。
      - P95 計算、日付フィルタ処理、DB 存在チェック、レポートの整形出力を実装。

  - データベース / 統合
    - DuckDB 統合（research / ai / その他集計で使用）。
    - monitoring 用 SQLite 初期化の冪等化（init_monitoring_db の呼び出しを追加）。

Changed
- 起動時のプロセス優先度設定を全ランナー（監視・実行）で実施するように変更（set_process_priority("high") を最初に実行）。
- run_monitoring の DB 接続挙動
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様に明示（監視データは環境分離しない設計）。
- run_execution の DB 接続挙動
  - paper_trading 環境時は paper_sqlite_path を使用して本番 DB とデータを分離。
- MONITOR_POLL_INTERVAL の取り扱い
  - 環境変数から整数値を読み取り、0 以下や不正な値はデフォルト（60 秒）へフォールバックするよう堅牢化（ログ警告を出力）。
- .env 自動読み込み
  - プロジェクトルートを __file__ から探索する方式により、CWD に依存しない自動ロードを実現。
  - OS 環境変数を保護する protected 機構を導入し、.env.local による上書きをサポート。

Fixed
- DB 接続のクリーンアップ
  - run_monitoring.py / run_execution.py で finally ブロックにより sqlite3 および duckdb 接続を確実にクローズするようにした（リソースリーク防止）。
- 監視 DB 初期化の冪等性確保
  - init_monitoring_db を起動シーケンス中で保証（存在しない場合作成、既存なら何もしない）。
- paper_verification_report の堅牢化
  - DB が存在しない場合のエラーメッセージを追加、SQLite の OperationalError に対するフォールバックを用意してレポート生成時に例外による全体停止を避けるようにした。
- process_priority / cpu_affinity のエラー耐性
  - psutil による権限不足や未実装機能に対して警告を出し、処理をスキップするようにして起動の失敗を回避。

Notes / 補足
- 初期リリースは「アルゴリズム的ロジック（ポートフォリオ構築・サイズ決定・ファクター計算）」と「運用周り（ランナー、監視、環境設定、プロセス優先度）」を両輪で整備した内容です。
- Paper Trading 用の分離（専用 SQLite）やニュース NLP の OpenAI 呼び出し設計など、実運用を意識した安全策（DB 分離、停止フラグ、API リトライ、入力検証、スコアクリップ）を多数導入しています。
- 今後の改善候補（コード中に TODO コメントあり）
  - position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）
  - 個別銘柄ごとの lot_size 管理（現状は全銘柄で共通の単元数）
  - ai/news_nlp の部分的失敗時のトランザクション保護やより細かい部分リトライ戦略

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時には、追加の変更点やマイナー修正を合わせて反映してください。）
KEEP A CHANGELOG形式に従い、コードベースから推測した変更履歴（日本語）を作成しました。初回リリース（v0.1.0）相当の内容としてまとめています。必要に応じて日付や項目の追加・調整を行ってください。

CHANGELOG.md
=============
全ての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

v0.1.0 — 2026-04-13
-------------------
初期リリース。以下の主要な機能追加・設計方針・実装を含みます。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて v0.1.0 として定義。

- 実行エントリと監視プロセス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離（設定: PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動。
    - duckdb 接続を使用して分析用 DB を利用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - プロセス優先度設定（高）を起動時に実施。監視中の例外はログに残してループ継続。

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
    - .env / .env.local 自動読み込み（プロジェクトルートの検出: .git / pyproject.toml 基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 環境変数の必須チェックや値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH など）および閾値（CPU/MEM/DISK）をプロパティとして提供。

- モニタリング DB 初期化ユーティリティ利用
  - init_monitoring_db が run_* スクリプトで呼ばれることで監視用テーブルが存在することを冪等に保証。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）から期間単位の検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - --from / --to / --db オプションに対応。期間フィルタは ISO8601 UTC 文字列で扱う。
    - デフォルトの評価基準（しきい値）を定義（例: 稼働率 >= 99%、P95 <= 200 ms 等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（メモリ内の純粋関数のみ、DB 参照なし）。
    - portfolio_builder: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）を実装。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限を適用する候補フィルタ（売却予定の銘柄をエクスポージャー計算から除外）。"unknown" セクターは制限を適用しない設計。
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear 対応、未知レジームはフォールバックで 1.0）。
    - position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に従う発注株数計算、単元丸め（lot_size）、各種上限（max_position_pct、max_utilization）・コストバッファを考慮した集約キャップのスケーリングを実装。
      - risk_based の場合は stop_loss_pct, risk_pct を用いた株数計算。
      - 余剰キャッシュを使った端数処理（lot 単位で再配分）を実装。

- プロセス優先度・CPU affinity ユーティリティ
  - utils/process_priority.py を追加。
    - Windows / POSIX を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- リサーチ・ファクター計算
  - research モジュールを追加（DuckDB 接続を受け取り SQL＋Python で実装、外部 API に依存しない）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時は None）。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等を計算（ウィンドウサイズ不足は None）。
      - calc_value: raw_financials から最新財務を結合して PER/ROE を計算。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。ホライズン検証（正の整数、最大 252 日）を実施。
      - calc_ic / rank / factor_summary: Spearman 相関（IC）計算、ランクセンシング（同順位は平均ランク）、各カラムの統計サマリを提供。
    - research.__init__ で zscore_normalize を data.stats から再エクスポート。

- ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py を追加。
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、記事数/文字数制限（最大記事数・最大文字数）でトークン肥大化を抑制。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンスのスキーマ検証（JSON Mode 期待、results キーと型チェック）、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗に備え、コードを限定して DELETE→INSERT を行うことで他銘柄の既存スコアを保護。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。
    - OPENAI_API_KEY の未設定時は明示的に例外を送出。

Changed
- 初期設計として、DuckDB を分析用、SQLite を監視/取引ログ用に使い分ける設計方針を明確化。
- Paper Trading と本番 DB の完全分離を明示（run_execution.py, Settings.paper_sqlite_path）。

Fixed / Improved
- 環境変数読み込みの堅牢化
  - .env パーサで export 付き行、クォート文字内のエスケープ、インラインコメントの扱いを改善。
  - auto-load の際に OS 環境変数を保護（protected set）して上書き制御を実装。
- ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL の値検証（1 未満や不正文字列は警告してデフォルトにフォールバック）。
- エラー耐性の強化
  - 監視ループ・ニュース NLP 等で例外発生時はログを残して処理を継続するフェイルセーフ動作を採用。
  - process_priority / cpu_affinity は権限不足や未対応 OS の場合に警告してスキップするよう改善。
- SQL/クエリ面の保守性
  - DuckDB 用クエリはウィンドウ関数・ROW_NUMBER を活用して最新財務などを効率的に取得するよう実装。
- 端数処理の明確化
  - position_sizing の aggregate cap スケーリングで lot 単位の切捨て・追加配分ロジックを導入し再現性を確保。

Security
- OpenAI API キーの取り扱いは引数優先／環境変数フォールバックとし、未設定時には ValueError を発生させることで誤った無認証呼び出しを防止。

Notes / Known limitations
- 一部の TODO/注意点をコード内に残しています（例: price 欠損時のフォールバック価格、将来的な銘柄別 lot_size 対応など）。
- news_nlp は API 呼び出しに依存するため、実運用では OpenAI の利用制限やコスト管理が必要です。
- position_sizing 等のパラメータ（risk_pct, stop_loss_pct, max_position_pct など）は実運用に応じたチューニングが必要です。
- DuckDB / SQLite のスキーマ（prices_daily, raw_financials, raw_news, trade_logs 等）は本 changelog に明示していません。スキーマの互換性に注意してください。

今後の予定（例）
- 単体テスト・統合テストの充実化（特に数値ロジックと DB クエリ周り）。
- ストラテジーのバックテスト基盤の統合と可視化ツールの追加。
- 銘柄別単元対応、手数料・スリッページのより詳細なモデル化。
- AI スコアの監査ログ・バージョン管理やキャッシュ機構の導入。

（以上）
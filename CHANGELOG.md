CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に準拠しています。  
重要な変更点は安定したリリース単位で記載しています。

v0.1.0 - 2026-04-13
-------------------

Added
- 初回リリース。
- 基本アーキテクチャと主要コンポーネントを実装。
  - 実行・監視用エントリポイント
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - 環境変数 KABUSYS_ENV が "paper_trading" の場合は paper 用専用 SQLite (デフォルト: data/paper_trading.db) を使用し、本番 DB と分離。
      - プロセス起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
      - duckdb へ接続して ExecutionEngine に渡す。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や非整数）の場合はデフォルトにフォールバックして警告ログを出力。
      - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB を参照・記録）。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.Settings 実装（環境変数・.env ファイル読み込みとラッパー）。
      - プロジェクトルートを .git または pyproject.toml で探索し、見つかれば .env → .env.local の順で自動ロード（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサは export 付き行、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
      - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種閾値など）と入力検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL のバリデーション）。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio.select_candidates: スコア降順 + signal_rank によるタイブレークで候補抽出。
    - portfolio.calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（全銘柄スコアが 0 の場合は等配分にフォールバックして警告）。
    - portfolio.apply_sector_cap: セクター集中上限チェック（"unknown" セクターは上限適用対象外）。売却予定銘柄をエクスポージャー計算から除外可能。
    - portfolio.calc_regime_multiplier: 市場レジームに基づく乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
    - portfolio.calc_position_sizes: 発注株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、per-stock 上限と aggregate 上限（available_cash）を考慮、必要に応じてスケーリングと端数配分を行う。cost_buffer による保守的コスト見積り考慮。
  - リサーチ・ファクター計算
    - research.calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足時は None）。
    - research.calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率。
    - research.calc_value: raw_financials から latest 財務データを取得して PER/ROE を算出。
    - research.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン計算、IC（スピアマン順位相関）計算、基本統計サマリなど。すべて DuckDB 接続を受け取り、外部 API には依存しない設計。
  - AI ニューススコアリング
    - ai.news_nlp.score_news: raw_news および news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む。
    - バッチ処理（最大 20 銘柄 / 呼び出し）、記事/文字数トリム（最大記事数・最大文字数制限）、スコアを ±1.0 にクリップ。
    - API の 429 / タイムアウト / ネットワークエラー / 5xx に対して指数バックオフで最大 _MAX_RETRIES 回リトライ。
    - レスポンスの厳密な JSON 検証、部分失敗時でも既存の他コードスコアを保護するため対象 code 絞って DELETE→INSERT を行う。
    - OPENAI_API_KEY 未設定時は明確な ValueError を送出。
  - 監視・検証ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を元に検証レポートを標準出力に生成する CLI を追加。
      - フィルタ期間指定 --from / --to、データベースパス --db オプションをサポート。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。閾値はソースコードで定義（例: 稼働率 99.0%、注文成功率 90.0%、P95 レイテンシ 200ms）。
      - データ不足・テーブル未作成時に例外を吸収し N/A 表示で継続可能。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を提供。CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。権限不足や未対応 OS の場合は警告を出してスキップ。

Changed
- 初回リリースのためなし。

Fixed
- 初回リリースのためなし。

Deprecated
- 初回リリースのためなし。

Removed
- 初回リリースのためなし。

Notes
- .env 読み込みはプロジェクトルートが検出できない場合にスキップされるため、パッケージ配布後や実行場所に依存しない安全な自動ロードを実現。
- run_monitoring は監視用 DB に対して常に settings.sqlite_path（本番 path）を使用するため、テスト環境で監視を回す場合は明示的な設定変更が必要。
- DuckDB を多用する計算モジュールは、データテーブル（prices_daily、raw_financials、raw_news など）を前提としている。これらのテーブルがない場合は部分的に N/A を返す挙動をとる。
- OpenAI 呼び出しを行う ai.news_nlp は API キー必須。API 呼び出しにはレート制限やネットワーク障害があるため、呼び出し側で適切なエラーハンドリングと再実行ポリシーを考慮すること。

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- このリリースは初期実装をまとめたものです。以降のリリースでテストカバレッジの追加、入力バリデーションやエラー処理の強化、性能改善を予定しています。
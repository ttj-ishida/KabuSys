CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。
バージョン番号はパッケージ内の __version__ に合わせてあります。

Unreleased
----------

- 今後の改善予定・TODO（コード内コメントより抜粋）
  - apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格導入（前日終値や取得原価等）。
  - position_sizing: 銘柄別の単元情報（lot_size）を stocks マスタから取得する設計への拡張。
  - news_nlp: API 呼び出しの部分的失敗に対するさらに細かな回復や監視強化。
  - ドキュメントの充実（運用手順・構成例・監視/運用 run スクリプトの説明など）。

v0.1.0 - 2026-04-12
-------------------

Added
- 基本機能・実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用する設計を採用。
    - 実行開始時にプロセス優先度を設定（高優先度）。
    - ExecutionEngine は RiskManager / OrderManager / Reconciler / OrderRepository を組み合わせてセッションを実行。
    - DuckDB を分析用ストアとして接続。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する（監視データは本番 DB に集約）。
    - 起動時にプロセス優先度を高に設定。

- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み）。  
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート囲み、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスで主要な設定値をプロパティ経由で安全に取得する仕組みを提供（型変換・バリデーション込み）。  
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE（instant/partial/never/reject の検証）、パス設定（duckdb/sqlite/paper_sqlite/pid/kill_flag）、
      しきい値（CPU/MEM/DISK）などを含む。

- 監視・運用関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動フローで呼び出し、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有に基づくセクター集中上限適用（unknown セクターは除外しない）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。  
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap に対するスケールダウン、cost_buffer による保守的見積り、残差配分ロジックを実装。
      - 価格欠損時のスキップと適切なログ出力を行う。

- リサーチ機能（DuckDB を利用）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時に None を返す仕様）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（null の伝搬を注意深く扱う）。
    - calc_value: raw_financials から最新財務データ取得し PER / ROE を計算。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（各ホライズン）を効率的に1クエリで計算。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）計算を実装（欠損や ties 対応、十分なサンプル数がない場合は None を返す）。
    - factor_summary / rank: カラムごとの基本統計量（count/mean/std/min/max/median）とランク付けユーティリティ。

  - research パッケージの公開インターフェースに zscore_normalize を含める（kabusys.data.stats から import）。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントを -1.0〜1.0 でスコア化し ai_scores に保存するフローを実装。
    - 最大バッチサイズ、記事・文字数トリミング、JSON Mode を前提とした出力バリデーション、スコアのクリップ、部分置換（DELETE + INSERT）による部分失敗耐性などを実装。
    - 429/ネットワーク断/5xx に対する指数バックオフによるリトライ処理を導入。
    - OPENAI_API_KEY 未設定時に ValueError を送出。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。  
      - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定（デフォルト閾値をソース内定義）。
      - DB パスの引数・環境変数対応と存在チェック、日付フィルタ (--from / --to) に対応。

- ユーティリティ
  - utils/process_priority.py
    - cross-platform なプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を吸収）。  
    - CPU affinity 固定機能（最初の N コアにピン留め）。権限不足等の失敗は警告でスキップ。

Changed
- （初回リリースのため該当なし）

Fixed
- config の .env パーサ強化により、クォート内のエスケープやインラインコメント、export プレフィックス等が正しく解釈されるようになり、環境変数読み込みの堅牢性が向上。
- run_monitoring._get_poll_interval: 不正な環境値や 0 以下の値を検出してデフォルトにフォールバックする仕様を導入（time.sleep の ValueError 回避）。

Security
- OpenAI API キーや機密情報は Settings / .env 経由で管理。自動ロードは OS 環境変数を保護する仕組み（protected set）を実装。

Removed
- （初回リリースのため該当なし）

Notes / Known limitations
- apply_sector_cap の価格欠損時の扱いに TODO が残る（過小見積りによりブロックが外れる可能性）。
- position_sizing は現時点で全銘柄共通の lot_size を想定している。将来的に銘柄別単元サポート予定。
- DuckDB の executemany 周りの注意点（空 params の扱いなど）に関するコメントがあり、バルク挿入時の guard が必要。
- news_nlp は外部 API へ依存するため API 制限や利用料金に注意。API エラー時はリトライや部分スキップでフェイルセーフを目指す設計だが、運用時の監視が推奨される。

開発者向け補足
- 環境変数の主なキー（デフォルト値はコード参照）:
  - KABUSYS_ENV (development | paper_trading | live)
  - SQLITE_PATH (data/monitoring.db)
  - DUCKDB_PATH (data/kabusys.duckdb)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - MONITOR_POLL_INTERVAL (60)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - OPENAI_API_KEY（news_nlp 用）
- パッケージバージョン: 0.1.0

ライセンスやその他の運用手順については別途ドキュメントにまとめる予定です。必要であれば CHANGELOG をセクション分けしてさらに詳細な運用ノートやマイグレーション手順を追記できます。
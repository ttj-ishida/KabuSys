CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に従っています。  
コード内容から推測して記載しています。実際のリリース日や変更履歴はリポジトリ管理履歴と照合してください。

Unreleased
----------
- ドキュメント化・小改善
  - news_nlp モジュールの一部ログ出力や部分的失敗時の扱いなど、追加の堅牢化・ログ改善の余地あり（コード内にフェイルセーフ設計あり）。
  - price フォールバック（前日終値や取得原価）の実装 TODO（position_sizing 内コメント）。

[0.1.0] - 2026-04-12
--------------------

Added
- コアパッケージ初期実装（バージョン: 0.1.0）
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 環境変数 KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db のデフォルト）を使用し、本番 DB と分離する動作を実装。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper/live に応じた振る舞いを想定）。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立て、RiskConfig（デフォルト値を含む）を設定して ExecutionEngine を起動。
    - プロセス優先度を初期に high に設定（utils.process_priority.set_process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告ログを出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - duckdb 接続も併用し、init_monitoring_db を呼ぶことで監視テーブルの存在を保証。
    - KeyboardInterrupt を捕捉して正常終了、最後に DB 接続をクローズ。
- 設定管理
  - config.py
    - .env 自動ロード実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順: OS 環境 > .env.local > .env（.env.local は上書き許可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサ: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォートなしの場合は '#' の直前が空白かタブのときのみコメント扱い）に対応。
    - 環境変数の検証ロジックを多数実装（必須キーチェック、KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証）。
    - 各種設定プロパティを提供（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk threshold 等）。
- モニタリング DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ（Windows と POSIX を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") 実装。実行権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count: Optional[int]) 実装。利用可能コア数を考慮して最初の N コアに固定。権限不足等は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター暴露を計算し、max_sector_pct を超えるセクターの新規候補を除外。sell_codes（当日売却予定）を考慮可能。unknown セクターは制限対象外。
    - calc_regime_multiplier: market レジームに基づく乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバックして警告ログ。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく株数決定ロジック。
    - 単元株（lot_size）丸め、max_position_pct・max_utilization による per-position / aggregate 上限、cost_buffer による保守的見積もり。
    - aggregate cap 超過時のスケーリングと残余キャッシュによる lot_size 単位での再配分アルゴリズムを実装。
    - 価格欠損時はスキップする挙動とログ出力。
- リサーチ／ファクター計算
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の SQL ウィンドウ関数を活用して各種ファクターを計算（MA200、ATR20、平均売買代金、PER/ROE など）。
    - データ不足（ウィンドウカウント不足）時は None を返す設計。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンを一括クエリで取得する実装（ホライズン入力バリデーションあり）。
    - calc_ic: スピアマン順位相関（IC）を実装。サンプル数 3 未満で計算不能なら None を返す。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティ。
  - research.__init__ で zscore_normalize（data.stats から）、上記関数群を公開。
- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出。
    - 処理は銘柄を最大 _BATCH_SIZE（デフォルト 20）ずつ API に送信。JSON Mode を期待するプロンプト（厳密な JSON 出力を要求）。
    - 1 銘柄あたり記事数・文字数上限でトークン肥大化を抑制（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - レート制限(429), ネットワーク断, タイムアウト, 5xx を対象に指数バックオフでリトライ（最大 _MAX_RETRIES）。
    - レスポンスのバリデーションとスコアの ±1.0 クリッピング、部分更新（対象銘柄のみ DELETE → INSERT）による部分失敗耐性。
    - API キー未設定時は ValueError を送出する明確なハンドリング。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を厳密に計算し、ルックアヘッドバイアスを避ける実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 向けの検証レポート生成ツール。コマンドライン引数 --from / --to / --db をサポート。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率・注文成功率・送信率・レイテンシ（P95）等を算出、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を行う。
    - P95 計算やデータ存在チェック、DuckDB/SQLite の OperationalError を捕捉して堅牢に動作する設計。

Changed
- .env 読み込みポリシー設計
  - OS 環境変数を保護する protected ロジックを導入し、.env.local は override=True で OS 環境変数を上書きしないが .env の上書きは可能とした。

Fixed
- 各種堅牢化
  - .env ファイル読み込み失敗時に警告を出して継続するようにして起動失敗を防止（warnings.warn）。
  - process_priority / cpu_affinity の権限不足・未実装関数呼び出しに対して警告でスキップするようにして、プラットフォーム間での安全な実行を確保。
  - calc_score_weights において全スコアが 0 の場合のフォールバック（等金額配分）を実装し ZeroDivision を回避。
  - run_monitoring の MONITOR_POLL_INTERVAL のバリデーション追加（0 以下や非整数の入力で ValueError を防ぎ、デフォルトに戻す）。
  - DB 初期化（init_monitoring_db）は冪等にして複数実行しても安全になるように配慮。
  - paper_verification_report の日付フィルタや P95 算出を堅牢化。テーブル未存在やデータ不足時は N/A 表示・FAIL 判定の取り扱いを追加。

Security
- 環境変数の必須チェック（_require）を導入し、未設定時に明示的な例外とメッセージを出力。

Notes / Known limitations
- ai/news_nlp.py は OpenAI API に依存。API キーが必要であり、API 側の挙動（レートや出力フォーマット）により一部銘柄のスコア取得が失敗する可能性がある設計になっている（部分更新で他銘柄データを保護）。
- position_sizing の価格欠損時の挙動については TODO コメントあり。将来的にフォールバック価格（前日終値等）を導入する余地がある。
- DuckDB の executemany 周りには互換性制約があるため、ai/news_nlp の書き込み実装は params が空でないことを確認する設計。
- run_monitoring は監視用 DB に常時本番 sqlite_path を使用するため、本番と同一 DB を使う構成でのテスト時は注意が必要（意図的な設計である旨をコードコメントに記載）。

今後の予定（参考）
- news_nlp のレスポンスバリデーション強化・失敗時の再試行・部分ロールバック戦略の改善。
- price フォールバックロジックの導入（position_sizing の TODO 対応）。
- ExecutionEngine / RiskManager 周りの監視・メトリクス出力強化。

-----------

参考:
- 設定とデフォルトは src/kabusys/config.py を参照してください。
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 主要モジュール: src/kabusys/portfolio/*, src/kabusys/research/*, src/kabusys/ai/news_nlp.py, src/kabusys/tools/paper_verification_report.py
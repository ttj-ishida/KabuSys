CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ この CHANGELOG はソースコードから推測して作成しています。実装意図や公開履歴に基づく正確な履歴ではなく、現状のモジュール追加・挙動・設定などをまとめた初期リリース向けの記述です。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
-------------------

初回リリース。以下の主要コンポーネントと機能を追加しました。

Added
- 基本パッケージ情報
  - kabusys.__version__ を "0.1.0" として追加。

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を呼び出す。
    - プロセス優先度を最初に "high" に設定する処理を導入。
    - duckdb 接続を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用する設計。
    - プロセス優先度を最初に "high" に設定する処理を導入。
    - check_once() 呼び出しで例外を捕捉し、ログ出力後にループ継続するフェイルセーフ実装。

- 設定・環境変数管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）。
    - 読み込み順: OS環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
    - .env 行パーサーを実装（export 形式、クォート/エスケープ、コメントの扱いに対応）。
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で提供：
      - データベース: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - Paper Trading: PAPER_FILL_MODE（instant|partial|never|reject、検証あり）
      - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
      - 環境: KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL
    - 必須環境変数取得ヘルパー _require() を追加（未設定時は ValueError）。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを run_execution.py/run_monitoring.py に組み込み（監視テーブルの存在を冪等に保証）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX を抽象化）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS を考慮して例外ではなく警告でフォールバック。

- Portfolio 構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位を返す。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を計算（スコア総和が 0 の場合は等分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックにより候補を除外する関数（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各配分方式（risk_based / equal / score）に基づく発注株数計算。lot_size 単位で丸め、aggregate cap（available_cash）超過時のスケールダウンと端数配分アルゴリズムを実装。コストバッファ（cost_buffer）考慮あり。

- Research / データ処理
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily/raw_financials テーブルを用いて各種ファクター（モメンタム・MA200 乖離、ATR、出来高、PER/ROE 等）を計算。
    - データ不足時の None ハンドリングや行数条件による判定を実装。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を LEAD を使って一括算出。ホライズン検証あり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク化、基本統計量集計を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ に zscore_normalize のエクスポートを含む集合エクスポートを追加。

- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores に書き込む処理を実装。
    - 処理フロー: タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）、銘柄ごとに記事をトリム（記事数・文字数上限）、最大 20 銘柄バッチで API 呼び出し、429/ネットワーク/5xx に対して指数バックオフでリトライ、レスポンス検証、スコアを ±1.0 にクリップ、部分失敗に強いテーブル置換（対象コードの範囲に限定した DELETE→INSERT）。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
    - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照しない設計。
    - 実装上の定数や上限（_BATCH_SIZE、_MAX_RETRIES、_MAX_ARTICLES_PER_STOCK 等）を定義。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。CLI で期間指定（--from/--to）と DB パス指定（--db）が可能。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ等を集計するロジックを含む。
    - 基準値（閾値）を定義し、PASS/FAIL 判定を行う。DB のテーブルが存在しない場合は安全に N/A を返す。
    - P95 計算や各種フォーマットユーティリティを実装。

Changed
- 監視・実行起動時の挙動
  - 監視 run_monitoring は MONITOR_POLL_INTERVAL に不正値が入った場合にログを出してデフォルトへフォールバックするようになった。
  - 監視は常に本番 sqlite_path を参照する仕様と明記（環境にかかわらず）。

- .env 読み込みの堅牢化
  - export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ、コメントの取り扱い、上書き制御（protected）などに対応。

Fixed
- 設計上の堅牢性向上
  - 各所での None / データ欠損時のハンドリングを追加（factor 計算やレポート生成、position sizing の価格欠損時スキップ等）。
  - プロセス優先度設定や CPU affinity 設定でアクセス権限不足や未サポート OS の場合に例外を投げず警告ログでスキップするようにした。

Notes / Implementation details
- DB
  - DuckDB を分析（prices_daily / raw_financials 等）に、SQLite を監視・発注ログ等の軽量ストレージに利用する想定。
  - init_monitoring_db() を起動時に呼ぶことで監視テーブルの存在を保障（冪等）。

- Paper Trading
  - paper_trading 環境ではブローカーは Mock を使用し、paper_trading 用 SQLite に完全分離して書き込みを行う。
  - PAPER_FILL_MODE（デフォルト "instant"）でペーパートレードの約定動作を制御。

- 環境変数（主なもの）
  - KABUSYS_ENV: development | paper_trading | live（必須だがデフォルトは development）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60、1 未満の値は無効）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
  - SQLITE_PATH: 監視等で使用する SQLite（デフォルト data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - OPENAI_API_KEY: ニュース NLP 用 API キー
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（"1"）

Migration / Usage notes
- 起動
  - 監視: python -m kabusys.run_monitoring または run_monitoring.py を実行。
  - 実行エンジン: python -m kabusys.run_execution または run_execution.py を実行。
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

- .env 自動ロード
  - プロジェクト内に .env や .env.local を配置すると自動的に読み込まれます（OS 環境変数が優先され、.env.local は .env を上書き）。
  - テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI ニューススコアリング
  - 実行時に OPENAI_API_KEY を設定するか、score_news() 呼び出し時に api_key を渡してください。未設定だと ValueError になります。
  - 大量 API 呼び出しやエラー発生時は指数バックオフでリトライしますが、恒常的な失敗時は部分的にスコアが取得できない可能性があります（設計上は他銘柄スコアを保護する更新を行います）。

Breaking Changes
- なし（初回リリース想定）。ただし設計上の仕様（監視の DB 選択や .env 自動ロード）に注意してください。

Security
- 現時点で特筆すべきセキュリティ修正はありません。環境変数や API キーの取り扱いには運用で注意してください（鍵は OS 環境変数や秘密管理により保護することを推奨）。

作者注
- 本 CHANGELOG はコードの内容から推測して作成しています。実際の公開リリースノートや変更履歴として使う場合は、リリースごとの検証やリリース担当者による確認を行ってください。
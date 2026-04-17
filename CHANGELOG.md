Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。プロジェクトの今回の初期リリース（v0.1.0）で導入された機能・挙動をコードベースから推測して整理しています。

CHANGELOG.md
=============
すべての変更はこのファイルに記載します。  
フォーマットは Keep a Changelog (<https://keepachangelog.com/ja/1.0.0/>) に準拠します。

v0.1.0 — 2026-04-17
--------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機能（プロジェクトルートの .env /.env.local）。OS 環境変数を保護するための protected オプションを採用。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - .env パーサは export プレフィックス、クォート、インラインコメント、エスケープをサポートする堅牢な実装。
      - 環境変数取得用 Settings クラスを提供（J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定等）。
      - 値検証ロジック（KABUSYS_ENV の有効値検査、LOG_LEVEL 検査、PAPER_FILL_MODE の有効値検査など）。
  - 実行/監視エントリポイント
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と分離。
      - プロセス優先度を起動時に "high" に設定する処理を追加（utils/process_priority.set_process_priority を使用）。
      - 停止フラグ（data/stop_requested.flag）を監視し安全に停止する仕組み。
      - 実行中の PID を data/execution.pid に記録する仕組み（pid_file 引数）。
      - OrderRepository、OrderManager、RiskManager（デフォルト設定）、Reconciler、ExecutionEngine の組み立てロジックを追加。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
      - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する挙動を採用。
      - 停止フラグ（data/stop_requested.flag）を検知してループ終了。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォームでプロセス優先度（Windows: HIGH_PRIORITY_CLASS 等 / POSIX: nice 値）を設定する set_process_priority(level) を実装。
      - CPU affinity を固定する set_cpu_affinity(cpu_count) を実装（権限不足時は警告を出してスキップ）。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: スコア降順選定（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター別エクスポージャ計算→上限超過セクターの候補除外、"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知値は 1.0 でフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。損切り率・リスク率・単元株丸め・per-position 上限・aggregate cap（利用可能現金を超える場合のスケールダウン）・cost_buffer（手数料等）対応。
    - src/kabusys/portfolio/__init__.py により上記関数を公開。
  - 研究・リサーチ機能（DuckDB ベース）
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（データ不足は None を返す）。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算（データ窓の最小行数チェック）。
      - calc_value: raw_financials と prices_daily を組み合わせた PER/ROE の計算（target_date 以前の最新財務レコードを取得）。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 将来リターン（複数ホライズン）計算。horizons 引数検証（正の整数かつ <= 252）。
      - calc_ic / rank / factor_summary: IC（スピアマン：ランク相関）、ランク付け（同順位は平均ランク）、ファクターの統計サマリー（count/mean/std/min/max/median）を実装。標準ライブラリのみで依存を抑制。
    - src/kabusys/research/__init__.py で主要関数を公開。
  - AI ニュース NLP（OpenAI を使ったニューススコアリング）
    - src/kabusys/ai/news_nlp.py
      - ニュースのスコアリング設計と実装（タイムウィンドウ計算、銘柄ごとの記事集約、バッチ送信、リトライ戦略、JSON レスポンスバリデーション、スコアクリップ等）。
      - 定数によるバッチサイズ、モデル名（gpt-4o-mini）、スコア上限、トークン肥大化対策（1銘柄あたりの記事数と文字数上限）等を定義。
      - score_news() は OPENAI_API_KEY の存在チェックとウィンドウ計算、記事取得・API 呼び出し・結果を書き込む流れを前提にしている（DuckDB の raw_news/news_symbols/ai_scores テーブルを参照）。
      - API エラー（429/ネットワーク/5xx）に対する指数バックオフリトライ方針の検討が組み込まれている。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプト。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し PASS/FAIL 判定を出力。
      - コマンドライン引数 --from / --to / --db をサポート。デフォルト DB は data/paper_trading.db。出力は標準出力。
  - DB/監視補助
    - monitoring_db.init_monitoring_db を run_* スクリプトで起動時に呼び出し、必要な監視テーブルが存在することを保証（冪等）。
    - DuckDB 接続は研究・AI・実行コンポーネントで共通利用。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- OpenAI API キーは必須（score_news は api_key 引数または環境変数 OPENAI_API_KEY を参照）。キー未設定時は ValueError を送出して安全に失敗。

Notes / 使い方・運用メモ
- 環境変数関連
  - .env 自動ロードの優先順位: OS 環境 > .env.local > .env。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - 主要な環境変数（抜粋）:
    - KABUSYS_ENV: development | paper_trading | live（必須の有効値チェックあり、デフォルトは development）
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。1 未満または不正値はデフォルトにフォールバック。
    - PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動（instant|partial|never|reject）。不正値は例外。
    - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
    - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
    - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - OPENAI_API_KEY: OpenAI 呼び出し用 API キー
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
- 停止フラグ
  - data/stop_requested.flag が存在すると run_monitoring/run_execution は安全に停止します。運用上、外部でこのファイルを作成することで安全停止を実現できます。
- 実行優先度
  - run_monitoring/run_execution は起動時に set_process_priority("high") を呼び出します。プラットフォームや権限によっては失敗・スキップされる旨をログに出します。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_trading 用 SQLite を使用して本番 DB から完全に分離します（テスト・検証用）。
- レポートツール
  - Paper Trading の検証レポートは CLI から呼び出せます:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DuckDB / SQLite
  - 研究系・AI系は DuckDB（軽量 OLAP）を利用し、価格・財務・ニュース等の分析を行います。実行系・監視系は SQLite を使用してトランザクションログ／監視ログを保管します。

既知の制約・今後の改善候補
- news_nlp 周りは API 呼び出し・部分失敗保護・レスポンスバリデーションに考慮がある一方、運用上のレート制御やコスト最適化は運用に応じた調整が必要です。
- position_sizing の lot_size は現状全銘柄共通の固定値（デフォルト 100）。将来的に銘柄別の lot_map を持たせる拡張を想定。
- apply_sector_cap のセクター評価は price_map の欠損時にエクスポージャが過少評価される可能性がある（TODO コメントあり）。将来的にフォールバック価格の導入を検討。

開発者向けメモ
- 全関数は可能な限り副作用を排し純粋関数として設計（ポートフォリオ構築・リサーチ関数群）。単体テストを書きやすい構成。
- DuckDB / SQLite のテーブルスキーマは各モジュールの期待項目に依存するため、テスト用の DB を用意する際は prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs / system_status / risk_logs 等のテーブルを整備してください。

ライセンス・著作権
- （この CHANGELOG はコードベースに基づく要約です。ライセンス情報はプロジェクトルートの LICENSE 等を参照してください。）

-- End of CHANGELOG.md --

必要があれば、項目の追加（たとえば実際のコミット単位での細かな変更点や各関数の API シグネチャ一覧、リリースノート英語版など）も作成します。どの粒度で記載するか指示してください。
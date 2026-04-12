CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語表記）

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-12
------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行/監視ランナー
  - run_execution.py:
    - ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を高に設定し、DuckDB/SQLite に接続して ExecutionEngine.run_session() を実行するフローを実装。
    - 環境が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てる。
    - RiskManager のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、初期ポートフォリオ値を broker.get_available_cash() から取得して設定。

  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非数）の場合はデフォルトにフォールバックして警告ログを出力。
    - 監視用途は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 例外耐性: monitor.check_once() で例外が発生してもログを残して次のポーリングに継続。

- 設定 / 環境読み込み
  - config.py:
    - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）。これにより CWD に依存せず .env 自動読み込みを行える。
    - .env / .env.local の自動ロードを実装（優先順位: OS 環境 > .env.local > .env）。テストなどで自動ロードを無効にするため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート。
    - .env パーサを強化:
      - export プレフィックス対応、引用符付き値のバックスラッシュエスケープ処理、コメントの扱い（クォート有無での取り扱い差分）などに対応。
    - Settings クラスを追加し、各種設定値をプロパティ経由で取得:
      - J-Quants / kabu API / LINE / DuckDB/SQLite パス（expanduser 対応）等。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許可）。
      - KABUSYS_ENV の検証（development, paper_trading, live）。
      - ログレベルの検証、各種閾値（CPU/MEM/DISK）や PID/KILLフラグ関連の設定プロパティを実装。
    - settings = Settings() をモジュール変数として提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告ログを出力。

  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有を考慮して、1セクター当たりの上限を超える場合は新規候補を除外。
    - レジーム乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py:
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score をサポート。
    - 単元株（lot_size）による丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウン、端数処理のための残差配分ロジックを実装。
    - cost_buffer により手数料等の保守的見積りを反映。

  - package export: portfolio/__init__.py で上記関数群をエクスポート。

- 研究・ファクター計算
  - research/factor_research.py:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20/相対ATR/平均売買代金/出来高比）、バリュー（PER/ROE）ファクター計算を実装。
    - DuckDB を用いた SQL ベース実装で prices_daily / raw_financials を参照。データ不足時の None ハンドリングを実装。

  - research/feature_exploration.py:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）、IC（スピアマン順位相関）calc_ic、ランク関数 rank、ファクター統計 summary を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。

  - research/__init__.py:
    - 主要 API をまとめてエクスポート（zscore_normalize を data.stats から取り込み）。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を calc_news_window で実装。
    - 記事集約、1銘柄あたり最大記事数/文字数によるトリム、最大 20 銘柄ずつのバッチ送信、JSON Mode による厳密なレスポンス期待、429/5xx/ネットワークエラーに対する指数バックオフリトライ、スコアの ±1.0 クリップを実装。
    - OpenAI API キー指定方法は引数優先 / 環境変数 OPENAI_API_KEY を参照。未設定時に ValueError を返す。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し、定義済み閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を出力。
    - 日付フィルタ (--from/--to)、--db オプションをサポート。DB が存在しない場合はエラーメッセージを表示。
    - 各種 SQL の実行時に sqlite3.OperationalError をハンドリングしてフォールバック。

- ユーティリティ
  - utils/process_priority.py:
    - Windows/Linux/Mac の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定するユーティリティを実装（psutil 利用）。
    - POSIX 系での nice 値、Windows での HIGH_PRIORITY_CLASS などをマッピング。アクセス拒否等が発生した場合は警告ログを出してスキップ。
    - set_cpu_affinity により最初の N コアに固定する機能を追加（引数検証と例外ハンドリングあり）。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Security
- OpenAI API キーは引数または環境変数から安全に解決し、未設定の場合は明示的エラーを発生させる実装を導入。

Notes / Known limitations / TODOs
- apply_sector_cap 内で price が欠損 (0.0) の場合、エクスポージャーが過小見積りされる可能性がある旨を TODO コメントで明記。将来的に前日終値や取得原価等のフォールバックの導入を検討。
- position_sizing では現在 lot_size を全銘柄共通で扱っている。将来的に銘柄別 lot_map への拡張を想定した TODO がある。
- DuckDB に対する executemany の扱い（空パラメータ禁止）への注意がコメントで残されているため、実運用でのパラメタ準備に注意が必要。
- ai/news_nlp.py は API レスポンスと DB 書き込みの一貫性を保つため部分更新（DELETE→INSERT）戦略を採用しているが、大規模運用時の競合制御やトランザクション処理は運用環境に依存する。
- run_monitoring のポーリングループは KeyboardInterrupt で正常終了するが、長期運用時のロギング/ローテーション・例外監視強化は今後の改善余地あり。

Acknowledgments
- 本リリースは、duckdb / psutil / openai SDK 等の既存ライブラリを活用して構築されています。
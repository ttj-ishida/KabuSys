CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
日付は本コードスナップショット作成日時（2026-04-12）を使用しています。

0.1.0 - 2026-04-12
-----------------

Added
- 初回リリース相当の主要機能群を追加。
  - 実行エントリ／デーモン
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient 経由で完全に分離されたペーパートレード実行ができる設計。
      - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority を利用）。
      - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てて run_session() を実行。
      - RiskManager に初期化パラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を注入。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告出力。
      - 監視は常に本番用 sqlite_path を使用（環境にかかわらず）。
      - 例外を捕捉してループ継続、KeyboardInterrupt を正しく処理して DB 接続をクローズする安全な終了処理を実装。

  - 設定管理
    - kabusys.config: 環境変数 / .env 自動ロード機構を実装（.env, .env.local をプロジェクトルートから読み込み）。
      - .git または pyproject.toml を基準にプロジェクトルートを探索（__file__ を基点に親ディレクトリを上るため CWD に依存しない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化対応。
      - .env パース改善:
        - export KEY=val 形式対応
        - シングル/ダブルクォート内のバックスラッシュエスケープ処理
        - クォート無し行でのインラインコメント判定（直前がスペース/タブの場合のみ）
      - Settings クラスに多くのプロパティを追加（J-Quants トークン、kabu API、LINE 設定、duckdb/sqlite パス、paper_trading 用 DB パス、監視閾値、PID/kill flag パス、env/log_level バリデーション等）。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
      - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
      - デフォルトパスは expanduser() により ~ 展開される。

  - ポートフォリオ構築（純粋関数群）
    - kabusys.portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順、signal_rank でタイブレークして最大 N を選出。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（スコアが全て 0 の場合はフォールバックと警告）。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中を判定して候補を除外（unknown セクターは除外しない）。当日売却予定銘柄をエクスポージャー計算から除外可能。
      - calc_regime_multiplier: market レジームに応じた資金乗数の提供（bull/neutral/bear、未知レジームは警告して 1.0 フォールバック）。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく発注株数計算。lot_size（単元）で丸め、per-position 上限、aggregate cap（available_cash）でスケーリング、cost_buffer による保守的見積り、端数処理（fractional remainder に基づく追加配分）をサポート。

  - リサーチ／ファクター計算
    - kabusys.research.factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 差分（ma200_dev）を DuckDB 上の prices_daily から計算。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を適切に扱う）。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務を取得）。
    - kabusys.research.feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン取得（horizons 入力検証あり）。
      - calc_ic: スピアマンランク相関（IC）をコード結合後に計算（有効レコードが 3 未満なら None を返す）。
      - factor_summary / rank: 基本統計量算出、同順位の平均ランク処理等の補助関数を実装。
    - kabusys.research.__init__ により主要関数をエクスポート（zscore_normalize は kabusys.data.stats から利用）。

  - ニュース NLP スコアリング
    - kabusys.ai.news_nlp
      - raw_news / news_symbols を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を利用して銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores に書き込む処理を実装。
      - 処理フロー: タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）、最大記事数/文字数トリム、バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）、部分失敗時の既存スコア保護（影響するコードのみ置換）などの設計方針を実装。
      - calc_news_window 関数を公開（JST→UTC での窓計算を明示）。
      - API キー未設定時は ValueError を送出。

  - 運用ツール
    - kabusys.tools.paper_verification_report
      - ペーパートレード用 SQLite を解析し、稼働率、注文成功率 / 送信率、リスク却下数、レイテンシ（平均・最大・P95）等のレポートを標準出力に出力するスクリプトを追加。
      - P95 算出、日付フィルタ（--from / --to）、DB 存在チェック、テーブル未存在時の例外捕捉によるフォールバックを実装。
      - レポートの合否判定（閾値はソース内定数で定義: 稼働率 99%、Fill 90%、Send 95%、P95 200ms）。

  - ユーティリティ
    - kabusys.utils.process_priority
      - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定（権限不足や未サポート環境では警告してスキップ）。
      - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を追加（cpu_count=None は何もしない）。引数検証とエラー耐性あり。
    - パッケージ初期化ファイル・バージョン
      - kabusys.__init__.__version__ = "0.1.0"

Changed
- （初回リリース）設計上の注意点や既知の振る舞いを明示。
  - .env 読み込みの保護（OS 環境変数は protected として上書きを制限）を導入。
  - DuckDB / SQLite 接続の扱いを明確化（monitoring は常に本番 sqlite_path を使う等）。

Fixed
- .env パースにおけるクォートやエスケープに関する耐性を向上（パース関数 _parse_env_line の改善により、クォート内のバックスラッシュやインラインコメントの扱いがより現実的に）。

Security
- OpenAI API キーは引数で明示的に渡すか環境変数 OPENAI_API_KEY を参照する設計。未設定時は明示的にエラーにすることで誤った公開を防止。

Notes / Breaking changes / Migration
- ペーパートレード:
  - KABUSYS_ENV=paper_trading を使用することで本番 DB と完全分離された data/paper_trading.db を使用します（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
  - PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。無効値は起動時に例外を発生させます。

- 環境変数自動読み込み:
  - デフォルトでプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）から .env / .env.local を自動読み込みします。テストや CI でこれを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env.local は .env の上書き（override=True）として読み込まれますが、すでに OS 環境変数に存在するキーは保護されます。

- 実行スクリプト:
  - run_monitoring は常に settings.sqlite_path を使用します。監視データを別 DB に分離したい場合は設定を変更してください（現バージョンでは本番用 path を用いる仕様）。

Known limitations / TODO
- position_sizing の price が欠損（0.0）の場合、エクスポージャーや発注量が過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバック実装を検討中。
- ai.news_nlp は API レスポンスフォーマットの厳密性に依存するため、実運用では response の堅牢な検証と再試行設計のチューニングが推奨される。
- research モジュールは DuckDB 上のテーブル（prices_daily / raw_financials 等）を前提としており、データ品質に依存する。zscore_normalize は外部 data.stats で提供されるため、連携を確認すること。

-----

この CHANGELOG はソースコードの構成・コメント・ドキュメントから推測して作成しました。追加のコミット履歴や意図した変更点があれば、追補します。
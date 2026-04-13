CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。
リリース日付のない項目は未リリースを意味します。

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期リリース（kabusys v0.1.0）
  - パッケージ情報: src/kabusys/__init__.py（__version__ = "0.1.0"）。
- 実行用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を最初に "high" に設定（utils.process_priority 経由）。
    - SQLite / DuckDB 接続を確立し、正常終了時にクローズする処理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db を既定）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を指定。initial_portfolio_value は broker.get_available_cash() から取得。
- 環境設定管理
  - src/kabusys/config.py を追加
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）を実装。優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パース処理はシングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。
    - 各種設定プロパティを提供（JQUANTS / KABU API / LINE API / DB パス / 監視しきい値 / 環境判定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/
    - portfolio_builder.py
      - select_candidates: スコア降順（同点は signal_rank 昇順）で候補抽出。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（WARNING）。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは無視）。
      - calc_regime_multiplier: レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数算出。単元株（lot_size）で丸め、per-stock 上限・aggregate cap、cost_buffer による保守的見積り、スケーリングと端数処理（残余キャッシュを用いた lot 単位の追加配分）を実装。
    - 上記関数はすべて DB 非依存でメモリ内計算（純粋関数）。
- 研究・ファクター計算モジュール
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）を計算。
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials と prices_daily を組合わせて PER / ROE を計算（target_date 以前の最新財務データを使用）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を計算。horizons の検証あり（1〜252）。
    - calc_ic, rank, factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、ファクター列の統計サマリーを提供。外部ライブラリ無しで実装。
  - research パッケージの公開 API を __all__ で整理（zscore_normalize を含む）。
- ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini + JSON Mode）でセンチメント評価し、ai_scores テーブルへ書き込むためのロジックを実装。
    - 処理フロー: タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC 変換）、記事集約（1 銘柄あたり最大記事数／文字数でトリム）、最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（該当 code のみ DELETE→INSERT）。
    - OpenAI API キー未設定時は ValueError を送出。
    - 各種定数（_BATCH_SIZE / _MODEL / _MAX_RETRIES / _MAX_ARTICLES_PER_STOCK 等）を定義。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）および CPU affinity を設定するユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップするフェイルセーフを実装。

Tools
- src/kabusys/tools/paper_verification_report.py
  - Paper Trading 用の検証レポート生成スクリプトを追加。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値（PASS/FAIL）はソース内に定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  - CLI オプション: --from / --to（YYYY-MM-DD）、--db（DB パス）。PAPER_TRADING_SQLITE_PATH 環境変数でも DB を指定可能。
  - DB が存在しない場合のエラーメッセージ、テーブル欠損時の耐性（OperationalError を捕捉してデフォルト値で処理）。

Changed
- 設計/実装上の重要な振る舞い（初版として明示）
  - .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の CWD 非依存設計）。
  - .env の上書きルール: OS 環境変数は protected として .env.local の override からも上書きされない（protected による保護）。
  - DuckDB / SQLite を併用するデータパイプライン設計（research は DuckDB を前提、監視/トレードログは SQLite を使用）。
  - Execution/Monitoring スクリプトは起動時にプロセス優先度を "high" にしようと試みる（失敗した場合は警告をログに出す）。

Fixed
- エラーハンドリングとフォールバックの改善
  - MONITOR_POLL_INTERVAL のパースで不正値（0 以下や非整数）を検出した場合、警告を出してデフォルト 60 秒にフォールバック（run_monitoring.py）。
  - PAPER_FILL_MODE の不正値に対して ValueError を投げる明示的なバリデーションを追加（config.Settings）。
  - process_priority.set_process_priority / set_cpu_affinity は権限不足や未実装例外を捕捉して警告に変換し、実行継続可能にした。
  - portfolio.calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし、WARNING を出力。

Known issues / Notes
- news_nlp モジュールは OpenAI API に依存しており、API の変化やトークン制限に影響される可能性がある。未解決の部分（大きなレスポンス時の部分的失敗処理の細部など）は今後改善の余地あり。
- position_sizing.calc_position_sizes の価格欠損時（price が 0.0）の扱いについて注釈あり（TODO: 前日終値や取得原価でのフォールバック検討）。
- .env パーサは多数の現実的ケースを扱うが、極端なフォーマットや非標準的なエスケープについて想定外の振る舞いをする可能性がある。
- research モジュールは prices_daily / raw_financials の整合性に強く依存する。データ不足時は None を返す設計。

Security
- OpenAI API キーなど機密情報は環境変数から取得する想定。README/.env.example を参照して適切に管理してください。

今後の予定（示唆）
- Engine の単体テストやモックブローカの拡充、news_nlp の堅牢化（部分失敗時のロールバック／トランザクション管理）、各アルゴリズムの性能検証・チューニング。
- lot_size を銘柄別にサポートするための拡張（stocks マスタへの lot_size 格納）。
- duckdb 実行時の executemany 制約に対するユーティリティの整備。

（以上）
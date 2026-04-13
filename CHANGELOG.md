CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリースは semver に従います。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- パッケージ初回リリース (バージョン 0.1.0)。
  - パッケージ識別: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 実行エントリポイント
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や文字列）の場合はデフォルトへフォールバックし、警告を出力。
    - 監視処理は本番 sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV に依存しない）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
    - SQLite / DuckDB 接続を確立し監視 DB 初期化を行ったのちポーリングを実行。KeyboardInterrupt により正常終了処理を行う。

  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading では Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続を併用。

- 設定・環境変数管理
  - config.py:
    - .env 自動ロード機能（プロジェクトルートの .git または pyproject.toml を検出して .env, .env.local を読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装の強化:
      - export KEY=val 形式対応、クォート（シングル/ダブル）処理、バックスラッシュエスケープ対応、インラインコメントルール。
      - override / protected オプションで OS 環境変数の上書きを制御。
    - 各種設定プロパティを提供:
      - DB パス: DUCKDB_PATH (デフォルト: data/kabusys.duckdb)、SQLITE_PATH (data/monitoring.db)、PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）
      - PID/KILL フラグパス、リソース閾値 (CPU/MEM/DISK) 等
      - KABUSYS_ENV 検証（development / paper_trading / live）
      - LOG_LEVEL 検証

- 監視周り
  - monitoring_db 初期化呼び出しを run_monitoring/run_execution で行う（冪等に DB スキーマを保証）。

- ユーティリティ
  - utils/process_priority.py:
    - Windows と POSIX (Linux, macOS, FreeBSD) を吸収してプロセス優先度を設定するユーティリティ（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates(): score 降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights(), calc_score_weights(): スコアが全て 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): 既存保有を元にセクター別エクスポージャーを計算し、1 セクター上限(max_sector_pct) 超過時に該当セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier(): 市場レジーム ("bull","neutral","bear") に応じた乗数を返す（未知のレジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method (risk_based / equal / score) に応じた株数計算。
    - 単元株（lot_size）丸め、max_position_pct による per-position 上限、max_utilization による aggregate cap、cost_buffer を用いた保守的コスト見積り、available_cash 超過時のスケーリングと端数処理を実装。

- リサーチ / ファクター計算（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum(), calc_volatility(), calc_value(): prices_daily / raw_financials を参照し、モメンタム、ATR 等のファクターを SQL と Python で計算。欠損データに対する安全処理あり（ウィンドウ不足で None を返す）。
    - DuckDB を用いたウィンドウ関数活用で効率的に集計。

  - research/feature_exploration.py:
    - calc_forward_returns(): 指定ホライズンの将来リターンをまとめて取得（horizons 検証あり）。
    - calc_ic(): Spearman ランク相関（IC）を計算、データ不足や定数分散のケースで None を返す。
    - rank(), factor_summary(): 同順位を平均ランクで扱うランク化と基本統計サマリー。

  - research/__init__.py:
    - 主要ファンクションをエクスポート（zscore_normalize は data.stats から取り込み）。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) に送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算して対象記事を抽出。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄当たり最大記事数 / 文字数制限でトークン肥大化を抑制。
    - API キー未設定時は明示的に例外を投げる。失敗時はログ出力してフェイルセーフ（部分成功でも残存データを保護）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、429/ネットワーク/5xx に対する指数バックオフ（リトライ上限あり）。
    - 出力 JSON の厳密化（システムプロンプト指定）と書き込み時の部分的更新戦略（DELETE→INSERT の対象絞り込み）。

- ツール
  - tools/paper_verification_report.py:
    - paper trading DB を解析して検証レポートを標準出力に出力。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を算出。
    - Pass/Fail 判定閾値を定義（稼働率 99%、成功率 90% など）。
    - DB が存在しない場合に分かりやすいエラーメッセージを表示。
    - CLI 引数 --from / --to / --db を提供。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可能。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API の利用は API キーが必須であり、未設定時は明示的にエラーを返す設計。キーは引数または環境変数 OPENAI_API_KEY で提供。

Notes / 動作上の注意
- .env 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。配布パッケージでの利用時は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能。
- run_monitoring は監視データを本番 sqlite_path に書き込むため、ローカルでモック等を使う場合は sqlite_path を適切に変更すること。
- run_execution は paper_trading モードで paper_sqlite_path を使用して本番 DB と分離する設計。
- process_priority の設定は OS 権限に依存するため、権限不足時は警告でフォールバックする。
- DuckDB を大量データで利用する際は SQL のスキャン範囲（コード内では calendar-day バッファ）に注意すること。

以上。今後のリリースではバグ修正、性能改善、テスト追加、CI/CD ワークフローやドキュメント強化を予定しています。
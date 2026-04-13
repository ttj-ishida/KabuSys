Keep a Changelog 準拠の形式で、コードベースから推測できる変更点を日本語でまとめました。初回リリース v0.1.0 として記載しています。必要なら項目を調整して下さい。

CHANGELOG.md
=============
全般方針
--------
- このファイルは Keep a Changelog のフォーマットに準拠しています。
- バージョン / 日付はコミット履歴がないためコード内容から推測して設定しています。

Unreleased
----------
- なし

0.1.0 — 2026-04-13
------------------
Added
- プロジェクト初期実装を追加。
  - パッケージ情報:
    - kabusys.__version__ = "0.1.0"
  - 環境設定管理:
    - kabusys.config.Settings 実装。
    - .env 自動読み込み機構（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local の読み込み順序と既存 OS 環境変数保護（override/protected の挙動）。
    - 環境変数検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック等）。
    - 多数の設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込み無効化。
  - 実行 / 監視エントリポイント:
    - run_execution.py — ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading のときは paper 用専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
      - ブローカークライアントは BrokerClientFactory を経由して生成（paper environment で Mock を想定）。
      - ExecutionEngine 周りの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
      - RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
      - DuckDB 接続を併用（analytics 用）。
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。
      - 環境にかかわらず監視は本番 sqlite_path を使用する設計。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
      - プロセス優先度設定（起動時に high を要求）。
      - KeyboardInterrupt のハンドリングと DB 接続のクリーンアップ。
  - 監視 DB 初期化ユーティリティ:
    - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。
  - ポートフォリオ構築:
    - kabusys.portfolio モジュールを追加（純関数群）。
      - portfolio_builder.py: select_candidates, calc_equal_weights, calc_score_weights（スコアが 0 の場合のフォールバックロジックを含む）。
      - risk_adjustment.py: apply_sector_cap（セクター集中除外ロジック）、calc_regime_multiplier（レジームに応じた乗数: bull/neutral/bear）。
      - position_sizing.py: calc_position_sizes（risk_based / equal / score の allocation_method をサポート、lot_size 単位で丸め、aggregate cap と scale-down ロジック、cost_buffer を考慮）。
  - 研究（Research）機能:
    - kabusys.research モジュール。
      - factor_research.calc_momentum / calc_volatility / calc_value（DuckDB を使ったファクター計算、ウィンドウ条件・データ不足時の None ハンドリング）。
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank（将来リターン計算、Spearman 相関（IC）計算、統計サマリー、ランク計算の実装）。
      - DuckDB を前提に SQL + Python の組合せで実装（外部 API 不使用）。
  - AI / ニュース NLP:
    - kabusys.ai.news_nlp モジュール。
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し、ai_scores テーブルへ書き込み。
      - タイムウィンドウ（前日15:00 JST 〜 当日08:30 JST）を明示的に計算する calc_news_window を提供（ルックアヘッドバイアス対策）。
      - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数/文字数トリム）、スコア ±1.0 にクリップ。
      - API 呼び出しのリトライ（429 / ネットワーク / 5xx に対するエクスポネンシャルバックオフ）設計。
      - APIキーは引数または環境変数 OPENAI_API_KEY で渡す。未設定時は ValueError。
  - ツール:
    - kabusys.tools.paper_verification_report — Paper Trading 検証レポート生成スクリプト。
      - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) をサポート。
      - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数。
      - パスが存在しない場合のエラーメッセージ、テーブルが無い場合のフォールバック処理を実装。
      - PASS/FAIL 判定基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
  - ユーティリティ:
    - kabusys.utils.process_priority:
      - cross-platform（Windows / POSIX）でプロセス優先度設定（high/normal/low）を提供。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
      - 権限不足や未対応環境では警告して処理をスキップするフェイルセーフ。
  - DB:
    - DuckDB（分析用）と SQLite（監視・paper_trading など）を併用する構成を採用。デフォルトパスは data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Deprecated
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- OpenAI API キーは引数または環境変数で明示的に指定する設計（秘匿情報の取り扱いに配慮）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の安全策）。

Notes / 実装上の注記（コードベースからの推測）
- run_monitoring は監視用 DB に常に本番 sqlite_path を使う設計のため、paper_trading 環境でも監視 DB は本番のパスが使われる点に注意。
- position_sizing.calc_position_sizes 内に price が欠損するとエクスポージャー過少見積になり得る旨の TODO コメントあり（将来的に価格フォールバックを検討）。
- settings.paper_fill_mode の値は強いバリデーションを行い、無効値は ValueError を送出するため環境変数設定ミスに注意。
- process_priority 系は権限不足（nice の制御など）で失敗する可能性があるため警告ログでフォールバックする実装。
- news_nlp の主要関数は外部 API に依存するため、API 失敗時は部分スキップして継続する（フェイルセーフ）。また JSON レスポンスのバリデーションを行う設計。

既知の制限 / 今後の改善候補
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別の lot_map を導入予定）。
- news_nlp の記事トリムやチャンク手法は現在の固定値（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）だが、柔軟化やトークン制限に応じた動的調整が有用。
- .env のパーサーはシンプルな実装（クォート処理やインラインコメント処理あり）だが、複雑な .env 構成での互換性を追加テスト推奨。
- DuckDB を利用したクエリはデータ量によっては重くなるため、インデックスやパーティショニング等のパフォーマンス最適化を検討。

---

必要であれば以下を追加できます:
- リリース日をコミット履歴に合わせて修正
- 各機能の利用方法・CLI オプション例・環境変数一覧を追記
- 既知のバグや Issue トラッキング番号の追加
CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、安定化された公開バージョンは日付付きで記載します。

[Unreleased]
------------

- （現在のリリースに向けた作業はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 基本アプリケーションと初期機能を追加（初回リリース: 0.1.0）。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
  - 設定/環境変数管理 (kabusys.config.Settings)
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
    - export 構文やクォート・インラインコメントの取り扱いに対応した .env パーサ実装
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート
    - 必須環境変数未設定時に ValueError を投げる _require() 実装
    - 各種設定プロパティを追加:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
      - PAPER_FILL_MODE（instant/partial/never/reject の検証）
      - PID/KILL フラグ関連パス（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）
      - 監視しきい値（CPU/MEMORY/DISK）
      - KABUSYS_ENV / LOG_LEVEL の検証（有効値の制約）
      - is_live / is_paper / is_dev ヘルパー

  - 実行エントリスクリプト
    - run_execution.py
      - ExecutionEngine 起動ロジック（スレッド実行、停止フラグの検知、PIDファイル管理）
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（data/paper_trading.db など）を使用して本番 DB と分離
      - BrokerClientFactory による Broker クライアント生成（MockBrokerClient を含む想定）
      - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て
      - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）と broker.get_available_cash() を初期ポートフォリオ値として使用
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）
      - 監視処理は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する設計
      - 停止フラグ (data/stop_requested.flag) による安全停止
      - 起動時にプロセス優先度を High に設定 (set_process_priority)
      - sqlite3 / duckdb 両方の接続を確保し、終了時にクローズ

  - 監視 DB 初期化ユーティリティ
    - monitoring_db.init_monitoring_db を用いて冪等に監視テーブルを保証

  - プロセス制御ユーティリティ (kabusys.utils.process_priority)
    - set_process_priority(level: "high"|"normal"|"low") 実装
      - Windows / POSIX の差分吸収 (psutil を使用)
      - アクセス権限や未対応 OS の場合は警告でスキップ
    - set_cpu_affinity(cpu_count: Optional[int]) 実装
      - cpu_count が None の場合は何もしない。例外・権限問題は警告でスキップ

  - ポートフォリオ構築ライブラリ (kabusys.portfolio)
    - portfolio_builder.select_candidates: スコア降順で候補選択（タイブレーク: signal_rank）
    - portfolio_builder.calc_equal_weights / calc_score_weights
      - スコアが全て 0 の場合のフォールバック（等金額配分）と警告
    - risk_adjustment.apply_sector_cap
      - セクター上限に基づく候補除外（unknown セクターは除外対象外）
      - 当日売却予定銘柄をエクスポージャー計算から除外する機能
    - risk_adjustment.calc_regime_multiplier
      - regime ("bull","neutral","bear") に応じた投下資金乗数（フォールバック: 1.0）
    - position_sizing.calc_position_sizes
      - allocation_method ("risk_based","equal","score") に対応
      - lot_size（単元）丸め、1 銘柄上限・aggregate cap によるスケーリング、cost_buffer 考慮、残差処理で lot 単位の追加配分ロジック

  - 研究・ファクター計算 (kabusys.research)
    - factor_research: calc_momentum, calc_volatility, calc_value
      - DuckDB の prices_daily / raw_financials テーブルを使用して各種ファクターを算出
      - 欠損データに対する安全処理（ウィンドウ内データ不足時は None）
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
      - 将来リターン、IC（Spearman ρ）計算、基本統計量の算出
      - pandas 等に依存しない純粋 Python 実装
    - research パッケージエクスポートに zscore_normalize（kabusys.data.stats 経由）を含む

  - ニュースNLP（AI）モジュール (kabusys.ai.news_nlp)
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能
    - 処理設計:
      - タイムウィンドウ計算（JST ベース → UTC に変換）
      - 記事を銘柄ごとに集約（最大記事数・最大文字数でトリム）
      - 20銘柄バッチ送信、429/ネット接続断/5xx に対するエクスポネンシャルバックオフリトライ
      - レスポンス検証・スコアクリッピング（±1.0）
      - 部分更新を想定した安全な ai_scores テーブル更新戦略（該当コードに限定して DELETE→INSERT）
    - OPENAI_API_KEY の使用と未設定時のエラー報告

  - ツール
    - tools.paper_verification_report
      - Paper Trading の検証レポートを生成する CLI
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（P95）等
      - デフォルト DB: data/paper_trading.db、--db オプションで上書き可能
      - パス／時刻フィルタ対応（--from, --to）
      - Pass/Fail 判定閾値の明文化（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）
      - DB スキーマが存在しない場合の安全処理

Changed
- 初回リリースにつき変更履歴なし

Fixed
- 初回リリースにつき修正履歴なし

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いは外部引数または環境変数（OPENAI_API_KEY）に限定し、未設定時は明示的に ValueError を発生させる実装

注意 / Breaking Changes
- run_monitoring の実行は「監視用途の DB」を環境にかかわらず設定された sqlite_path（Settings.sqlite_path）を使用する設計になっています。paper_trading 環境で監視を分離したい場合は sqlite_path を明示的に差し替えてください。
- Settings の環境変数検証により、KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などに無効な値を与えると起動時に例外が発生します。運用環境での環境変数設定に注意してください。
- process_priority や CPU affinity の設定は権限不足・プラットフォーム非対応時に警告でスキップされます（処理は継続）。スクリプトはこれら失敗を致命的としませんが、期待通りの優先度設定が行われていない可能性があります。

開発メモ / TODO（コード中注記）
- position_sizing の price が欠損（0.0）だった場合のフォールバック価格（前日終値や取得原価）の導入検討
- news_nlp の OpenAI 呼び出し後の DB 書き込み周りは部分失敗を考慮した安全性が意図されている（DELETE→INSERT の設計） — 実装の詳細なテスト推奨
- 将来的に銘柄ごとの lot_size を stocks マスタで持たせる拡張を想定

References
- 各モジュールの詳細は該当ソースファイル内の docstring を参照してください（kabusys/ 以下）。
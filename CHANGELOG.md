CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは Keep a Changelog の様式に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本リリース: KabuSys 自動売買フレームワークの初期機能群を追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV により paper_trading（MockBrokerClient）と本番を切り替え、paper_trading 時は data/paper_trading.db を専用 DB として使用する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
  - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）により外部からの停止制御に対応。
  - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを追加。

- 設定管理
  - config.py: .env / .env.local の自動ロード機能を実装（OS 環境変数を上書きしない安全なデフォルト）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 複数の設定プロパティを追加: DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE（バリデーションあり）、PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU/MEMORY/DISK 閾値、LOG_LEVEL、KABUSYS_ENV（development/paper_trading/live）など。
  - .env のパースを強化（export 形式、クォート、エスケープ、インラインコメントの扱いなどに対応）。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全て 0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。レジームに対するデフォルト乗数マップを提供し、不明レジームは警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing: 株数決定ロジック（allocation_method: "risk_based", "equal", "score"）を実装。単元株丸め（lot_size）、最大ポジション比率、利用可能現金に対する aggregate cap、cost_buffer（手数料・スリッページ見積り）などに対応。投資額スケーリング時の端数処理ロジックを実装。

- 研究・リサーチモジュール
  - research.factor_research: DuckDB を使ったファクター計算を実装（モメンタム: 1/3/6 か月リターン、MA200乖離・ボラティリティ: ATR20・相対 ATR・平均売買代金、バリュー: PER/ROE）。データ不足時の None 処理、ウィンドウ計算等に配慮。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC 計算（Spearman ランク相関）、ファクター統計サマリ（count/mean/std/min/max/median）、ランク処理を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats 依存）をエクスポート。

- AI / ニュース NLP
  - ai.news_nlp: raw_news テーブルを集約し OpenAI（gpt-4o-mini）でセンチメントを付与する機能を実装。ニュース集計時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく選別、1 銘柄当たりの最大記事数 / 文字数トリム、最大バッチサイズ、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時のデータ保護（対象コードに限定して DELETE→INSERT）などの設計方針を採用。
  - calc_news_window ユーティリティを追加（UTC でのウィンドウ計算）。

- ユーティリティ
  - utils.process_priority: psutil を用いてクロスプラットフォームでプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。権限不足・未対応 OS の場合は警告ログを出して安全にスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定（閾値はソース内定義）。コマンドライン引数で期間指定（--from, --to）と DB パス指定（--db）に対応。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を実行して監視テーブルを冪等に初期化する呼び出しを各起動スクリプトに追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ai.news_nlp.score_news は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）の存在を必須とし、未設定時は ValueError を送出することで誤動作を防止。

Notes / Known limitations / TODOs
- price が欠損（0.0）の場合の扱い
  - apply_sector_cap 内で price が 0.0 の場合、エクスポージャーが過少見積になりブロックが外れる可能性がある旨を注記。将来的に前日終値や取得原価をフォールバックする検討が必要（ソースに TODO コメントあり）。
- DuckDB の executemany に関する注意
  - ニュース NLP の書き込みで部分失敗時の保全（DELETE WHERE ... → INSERT）や executemany 前に params が空でないことを確認する実装上の配慮がある（DuckDB 0.10 の制約）。
- psutil によるプロセス優先度設定は権限が必要。権限不足時は警告ログを出して動作を継続するため、期待どおりに優先度が変わらないことがある。
- research モジュール・ai モジュールは大量データを扱うため、実行環境のリソースに依存する。DuckDB とメモリ使用量を考慮した運用が必要。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックし、ログで警告を出す設計。戦略側でレジームに応じたシグナル制御を行うことを想定。
- Paper Trading は本番 DB と完全に分離するが、運用時は PAPER_TRADING_SQLITE_PATH の確認を推奨。

環境変数（主要）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker 動作モード（instant|partial|never|reject、デフォルト "instant"）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp で必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証情報（必須項目として Settings が参照）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL など多数（詳細は config.py を参照）

CLI / 実行例
- 監視起動:
  - python -m kabusys.run_monitoring
- エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH で代替可）

開発者向けメモ
- パッケージのバージョンは src/kabusys/__init__.py に __version__ = "0.1.0" として定義。
- 自動 .env ロードはプロジェクトルートの検出（.git または pyproject.toml）で行われ、配布後の挙動も考慮して __file__ を起点に探索する実装になっている。

以上。
# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- 開発中の変更点はここに記載します。

---

## [0.1.0] - 2026-04-17

初回リリース。KabuSys のコア機能群を追加しました。主な追加内容をモジュール別にまとめます。

### Added

- コアパッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する（監視テーブルの初期化を行う）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - `check_once()` の例外を捕捉してログ出力し、ループ継続するフェイルセーフを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（`data/paper_trading.db`）に完全分離して記録する。
    - 停止フラグでエンジン停止、PID ファイル取り扱い、スレッドで実行されるセッションの監視を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
    - `.env` / `.env.local` の読み込み順序と上書き制御（OS 環境変数の保護）を実装。
    - `.env` 行パーサは `export KEY=...`、クォート（シングル/ダブル）のエスケープ処理、インラインコメントの扱いなどに対応。
    - 各種設定プロパティを追加（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode の検証、PID/KILLフラグパス、閾値設定、env/log_level の検証など）。
    - `Settings` クラスと `settings` シングルトンを提供。

- 監視/メトリクス関連
  - monitoring_db 初期化を起動スクリプトから確実に呼び出す実装（冪等なテーブル初期化）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - コマンドライン引数 `--from`, `--to`, `--db` に対応。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL を判定（閾値はソース内に定義）。
    - P95 計算、期間フィルタ、DB が存在しない／テーブル不足時のフォールバック（N/A 表示）を実装。
    - デフォルト DB パスは `data/paper_trading.db`。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、同点は signal_rank 昇順）と候補選定。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックして警告出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。既存保有のセクター別時価を算出して、上限超過セクターの新規候補を除外する（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull":1.0、"neutral":0.7、"bear":0.3、未知は 1.0 フォールバックで警告）。

  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap を考慮したスケーリング、余りの配分ロジックを実装。
    - 手数料・スリッページ見積り用 cost_buffer を考慮。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を使ったファクター計算を実装（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER・ROE）を計算する純粋関数を提供。

  - research/feature_exploration.py
    - 将来リターン（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - 外部依存を用いず標準ライブラリのみで実装。

  - research/__init__.py
    - 主要な研究関数群と zscore_normalize（data.stats から）をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント分析して ai_scores に書き込む処理を実装。
    - 処理設計: タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）、銘柄ごとの記事集約（最大記事数・文字数トリム）、バッチ送信（最大 20 銘柄）、エラーリトライ（429/ネットワーク/5xx に対して指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）など。
    - API キー解決、ニュースウィンドウ計算ユーティリティ（calc_news_window）を実装。
    - （注）ファイル末尾が切れている箇所があり、完全な実装はソース内で継続されています。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応し、優先度レベル ("high"/"normal"/"low") を受け取る。
    - CPU アフィニティ設定ユーティリティ set_cpu_affinity を追加。
    - アクセス権や未対応機能時には警告を出してスキップする安全設計。

### Changed

- （初回リリースのため「変更」は無し）既存プロジェクトへの導入時は、環境変数・DB パス・API キー等の設定に注意してください。

### Fixed

- （初回リリースのため「修正」は無し）

### Notes / 注意点 / TODO

- config._load_env_file の自動ロードはプロジェクトルートが特定できない場合はスキップされます。テスト環境等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- portfolio/risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積になる旨の TODO コメントがあります。将来的には前日終値や取得原価でのフォールバックの導入を検討しています。
- position_sizing の将来的拡張として銘柄別 lot_size を導入する TODO が残っています（現状は全銘柄単一の lot_size を想定）。
- ai/news_nlp.py は設計上リトライや部分更新に備えた堅牢な実装方針が示されていますが、ファイル末尾が途中で切れているため一部処理が未表示です。実運用前に完全実装を確認してください。
- run_monitoring は監視に本番 SQLite を使用するため、テスト環境で誤って本番 DB を操作しないよう注意してください（paper_trading は run_execution で専用 DB を使用することで分離されています）。
- set_process_priority / set_cpu_affinity は実行環境の権限に依存します。AccessDenied 発生時はログに警告を出して処理を続行します。

---

今後の予定（例）
- ai/news_nlp の完全実装とバッチ実行の統合テスト
- 銘柄別 lot_size の導入と stocks マスタの追加
- モニタリングのアラート送信（LINE 連携等）とより詳細なメトリクス収集

--- 

（この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴やリリースノートとは差分がある可能性があります。）
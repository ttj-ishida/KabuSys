# CHANGELOG

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
コードベースの内容から機能追加・変更点を推測して記載しています。

すべてのリリースノートは日本語で記載しています。

## [Unreleased]

### 注意 / 進行中
- research/factor_research.py の実装が途中で切れている箇所があります（`calc_momentum` の末尾が不完全）。今後のリリースで完成予定です。
- 一部に TODO コメント（価格のフォールバック、銘柄別 lot_size の導入等）が残っています。これらは次期リリースで対応を検討します。

---

## [0.1.0] - 初回リリース
リリース日: 2026-04-18（コードの日付やファイル内容から想定）

### 追加 (Added)
- 基本アプリケーションパッケージを実装
  - パッケージ情報: `kabusys/__init__.py` にバージョン `0.1.0` を追加。
- 実行系スクリプト
  - `run_execution.py`:
    - ExecutionEngine を起動するエントリポイントを実装。
    - 環境に応じて paper_trading 用 DB（`data/paper_trading.db`）を使用する機能を実装（`KABUSYS_ENV=paper_trading` 時は mock ブローカーを想定）。
    - 停止フラグ（`data/stop_requested.flag`）検知による安全停止、実行 PID ファイル（`data/execution.pid`）利用、デーモンスレッドでの実行ループ等を実装。
    - ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行う。
- 監視系スクリプト
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様を明記。
    - 停止フラグ検出でループを終了し、例外時はログを出して次回ポーリングへ復帰する堅牢化。
- 設定管理
  - `config.py`:
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序、OS 環境変数保護（protected）を実装。
    - 複雑な .env パースロジックを実装（export 形式、クォート文字とバックスラッシュエスケープ、インラインコメント処理などを考慮）。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、paper_trading 用パス、監視閾値、環境判定メソッド等）。
    - `Settings` クラスおよびグローバル `settings` インスタンスを提供。
- 設定ユーティリティ CLI
  - `config_setup.py`:
    - 対話式ウィザードで `.env` を作成・更新する CLI を実装。
    - 入力支援、シークレットマスク、デフォルト・選択肢の提示、確認後のファイル書き込みを行う。
    - `.env` のテンプレート書き出し機能を実装。
  - `validate_config.py`:
    - 起動前に必須環境変数や設定ファイルの存在/妥当性を検証する CLI を実装。
    - `--strict` オプションで警告も失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップする旨の警告表示。
    - DB パスや本番環境向けガード（LINE 通知設定、KILL_FLAG の自動クリア設定等）をチェック。
- ポートフォリオ構築ライブラリ
  - `portfolio/portfolio_builder.py`:
    - 候補選定 select_candidates（スコア降順、同点は signal_rank）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全てのスコアが 0 の場合はフォールバックで等金額配分）を実装。
  - `portfolio/risk_adjustment.py`:
    - セクター集中抑制 apply_sector_cap（既存保有のセクター別エクスポージャー計算に基づいて新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - `portfolio/position_sizing.py`:
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score" に対応）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、残余キャッシュでの端数配分アルゴリズムを実装。
    - cost_buffer による保守的コスト見積りをサポート。
  - `portfolio/__init__.py` で主要 API をエクスポート。
- ユーティリティ
  - `utils/logging_setup.py`:
    - 統一ログ設定関数 `setup_logging` を実装。
    - stdout への StreamHandler（標準出力）、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 引数 / 環境変数 / デフォルトの優先順位でログレベル・ログディレクトリを解決。
  - `utils/process_priority.py`:
    - プラットフォーム差分を吸収したプロセス優先度設定 `set_process_priority` 実装（Windows と POSIX の nice の違いを吸収、失敗時は警告出力してスキップ）。
    - CPU affinity 設定 `set_cpu_affinity` を提供（利用可能なコア数に合わせて最初の N コアに固定）。
- 監視データベース初期化
  - `monitoring/monitoring_db.py`（インポート参照あり）を用いて起動時に監視テーブルを冪等で初期化する仕組みを導入（run_monitoring と run_execution の両方で呼び出し）。
- 実行検証ツール
  - `tools/paper_verification_report.py`:
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数などをレポート出力する CLI を実装。
    - 判定閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from/--to）と DB パスオーバーライド（--db）をサポート。
- research/factor_research.py の基礎
  - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計を追加（calc_momentum などの関数を含む。実装は一部未完）。

### 変更 (Changed)
- ログ出力の方針
  - ログは stdout をメインに使用する（cron や Task Scheduler のリダイレクトを想定）。ファイル出力は補助（TimedRotatingFileHandler）。
- .env の自動読み込み仕様を明確化
  - OS 環境変数を保護しつつ `.env` と `.env.local` の読み込み順序を規定（`.env.local` は override=True）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

### 修正 (Fixed)
- エラーハンドリングの改善
  - run_monitoring のポーリング内での予期しない例外をキャッチしてログ出力した上で次のポーリングに進むようにし、監視プロセスのクラッシュ防止を実装。
  - logging_setup がログディレクトリ作成失敗時に明確な警告を出してファイルハンドラをスキップするようにした。
  - process_priority の権限不足や未対応プラットフォームでの失敗を警告し、安全にスキップする処理を追加。

### ドキュメント・補助 (Documentation)
- 各モジュールに docstring を追加し、関数の挙動・引数・返り値・注意点を明記。
- config_setup と validate_config に CLI 使用方法・説明を追記。

### 既知の制約 / TODO
- price_map に価格が欠損した場合のフォールバックロジックは未実装（TODO コメントあり）。
- 銘柄別の単元株（lot_size）管理は未対応。将来的に stocks マスタの導入を想定した TODO 有。
- research モジュールの一部（ファクター計算）が未完成。
- 一部のエラー条件（例: SQLite/DuckDB ファイルの不整合や権限問題）に対するユーザー向けリカバリ手順や詳細なドキュメントは今後整備予定。

---

## 参考: 主要な環境変数とデフォルト値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

---

この CHANGELOG はコードの中身から推測して作成しています。実際の変更履歴やリリース日付は実プロジェクトの管理履歴（Git タグ・コミットログ）に基づいて確定してください。必要であれば、Git コミットログやタグからより正確な CHANGELOG を生成する手順も案内します。
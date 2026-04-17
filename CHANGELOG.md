# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースからの推測に基づいて作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-17

初期リリース。日本株自動売買システム KabuSys の基礎機能を実装しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージバージョン: `__version__ = "0.1.0"` を導入。
- 環境設定・読み込み
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。  
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ファイルのパース実装（コメント、`export KEY=val`、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを追加し、アプリケーション設定（J-Quants / kabu API / DB パス /監視閾値 等）を環境変数から取得する API を提供。
  - 必須設定を要求する `_require` 実装（未設定時は例外を投げる）。
- 設定ウィザード CLI
  - `kabusys.config_setup` により対話式で .env を作成/更新するウィザードを追加。
  - 保存テンプレートは機密項目をマスクしつつ .env を出力（README 相当のヘッダを含む）。  
  - 推奨値・選択肢を提示（KABUSYS_ENV, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。環境変数および config/*.yaml の存在・基本妥当性をチェック可能。
  - `--strict` モードをサポート（警告を FAIL 扱いにする）。
  - PyYAML が無ければ YAML 検証をスキップし警告を出す挙動。
  - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE 設定未設定や Kill Flag の危険設定など）。
- 実行エンジン起動スクリプト
  - `kabusys.run_execution` を追加。ExecutionEngine を起動するエントリポイント。
  - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` / 環境変数）。
  - BrokerClientFactory の利用によりペーパートレード時に MockBrokerClient を使用可能（設定に応じた分離）。
  - 停止フラグ（data/stop_requested.flag）と execution.pid を使用した起動/停止制御を実装。
  - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立て例を実装。
  - RiskManager にデフォルトの RiskConfig パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定。
- 監視ループ起動スクリプト
  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループを起動するエントリポイント。
  - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - 監視は環境にかかわらず本番の sqlite_path を使用する（監視 DB は本番 DB を参照）。
  - 停止フラグ（data/stop_requested.flag）検知でループを安全に終了する。
  - DB 初期化用に init_monitoring_db を呼び出し、テーブル存在を保証（冪等）。
- DB / 分析基盤
  - DuckDB 接続の初期化（`Settings.duckdb_path`）を導入し、分析処理で利用可能に。
- プロセス管理ユーティリティ
  - `kabusys.utils.process_priority` を追加。プラットフォーム抽象化されたプロセス優先度設定を提供（Windows、POSIX サポート）。
  - `set_process_priority(level)`（"high"|"normal"|"low"）と `set_cpu_affinity(cpu_count)` を実装。
  - 許可/未対応時は警告を出してフォールバック。
- ポートフォリオ構築ライブラリ（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank を使用）。
    - 等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックし警告。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap（既存保有のセクター比を計算し上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - ポジション株数計算 calc_position_sizes（allocation_method: risk_based|equal|score）。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（available_cash）に基づくスケーリングと端数処理を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加（DuckDB を用いたファクター計算）。
  - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20 等）、流動性指標を計算する関数を実装。価格テーブルは `prices_daily` を参照。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。ペーパートレードの検証レポート生成ツール。
    - 稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（P95）等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パス: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで指定可能）。
    - P95 計算、期間フィルタ（--from/--to）に対応。
- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db`（監視用テーブルを冪等に初期化）を各起動スクリプトから呼び出すように統一。
- 操作・運用面のデフォルトと安全策
  - デフォルト値の明示化（MONITOR_POLL_INTERVAL=60、DUCKDB_PATH/SQLITE_PATH のデフォルトなど）。
  - 無効な環境変数値（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）に対する検出と警告/例外処理を実装。
  - .env を Git にコミットしないように README/ヘッダで注意喚起。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- .env ファイルに機密情報（API トークン・パスワード）を保存する設計のため、config_setup のヘッダで「.env を Git にコミットしない」旨を強調。
- Settings._require により必須機密値が未設定の場合に起動前に失敗することで誤設定による機密露出や運用ミスを防止。

---

## マイグレーション / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を必ず設定してください。未設定だと Settings のプロパティアクセスで例外になります。
- 実行環境:
  - KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかを設定してください（大文字小文字は無視）。
  - paper_trading を使う場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を用いるため本番 DB と完全に分離されます。
- 監視:
  - run_monitoring は MONITOR_POLL_INTERVAL でポーリング間隔を設定できます（正の整数、デフォルト 60 秒）。
  - 監視は監視用 sqlite_path を参照します（Settings.sqlite_path）。monitoring は常にこの sqlite_path を参照する設計。
- 停止 / PID 管理:
  - 実行中停止はプロジェクトルート下の data/stop_requested.flag を作成することで制御します。execution は data/execution.pid を使用します。
- CLI:
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

以上。必要があれば各機能ごとのより詳細な変更点・実装上の注意点を追記します。
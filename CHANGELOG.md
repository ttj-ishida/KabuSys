# CHANGELOG

すべての重要な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

初回公開リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定・読み込み
  - .env 自動読み込み機能を追加。読み込み順は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env のパースを強化：
    - export KEY=val 形式対応
    - シングル／ダブルクオート内のバックスラッシュエスケープ対応
    - 行内コメントの扱い（クォートの有無での判別）に対応

- Settings（設定取得ラッパー）
  - 環境変数をプロパティ経由で取得する `Settings` クラスを追加：
    - J-Quants / kabuステーション / LINE / データベース / 監視閾値等の設定を提供
    - `env`, `is_live`, `is_paper`, `is_dev` 等のユーティリティプロパティ
    - `paper_fill_mode` のバリデーション（instant/partial/never/reject）
    - パス系は `pathlib.Path` を返す（`duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`）

- 設定ウィザード CLI
  - 対話式で .env を生成・更新する `kabusys.config_setup` を追加。
  - デフォルト値、選択肢、シークレット入力、確認プロンプト、保存処理を実装。
  - `python -m kabusys.config_setup` で実行可能。

- 設定検証 CLI
  - `.env` や `config/*.yaml` の設定不備を検出する `kabusys.validate_config` を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、
    YAML ファイルの存在とパースチェック（PyYAML 未インストール時はスキップ）を実装。
  - `--strict` オプションで警告を FAIL 扱いにする機能。
  - `python -m kabusys.validate_config` で実行可能。

- 実行・監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプト `kabusys.run_execution` を追加：
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper トレード用 DB（`data/paper_trading.db` / 環境変数で上書き）を使用し MockBroker を利用する設計を反映。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動を実装。
    - 停止はプロジェクトの `data/stop_requested.flag` により検出し安全に終了。
    - 実行中は PID ファイルを書き込む（`data/execution.pid` デフォルト）。

  - SystemMonitor 起動スクリプト `kabusys.run_monitoring` を追加：
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB 接続を初期化してポーリングループで `SystemMonitor.check_once()` を定期実行。例外発生時はログを出して次ポーリングへフォールバック。
    - 停止フラグファイルでループを抜け、接続を確実にクローズするように実装。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report` を追加。
  - Paper Trading 用 SQLite DB を集計して以下指標を計算・出力：
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。
  - CLI オプションで期間指定（--from / --to）および DB パス指定（--db）。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照。
  - 合格基準（しきい値）を定義し PASS/FAIL 判定を出力（デフォルト閾値はコード内定義）。

- ポートフォリオ構築ライブラリ
  - 銘柄選定 / 重み付け
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計 0 の場合はフォールバック）を追加
  - セクター集中排除・レジーム乗数
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull/neutral/bear のマッピング、未知はフォールバック）
  - ポジションサイジング
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて買付株数を計算、lot 単位丸め、1 銘柄上限と aggregate cap（available_cash）に基づくスケーリングと余剰分の割当ロジックを実装。
    - cost_buffer（スリッページ・手数料見積）を考慮した計算。

- 研究（Research）モジュール
  - ファクター生成モジュール `kabusys.research.factor_research` を追加（DuckDB を利用して prices_daily / raw_financials から計算）。
  - モメンタム、長期移動平均乖離、ATR（ボラティリティ）、流動性指標などの計算ロジックを実装（関数例: calc_momentum, calc_volatility）。
  - 設計方針として DuckDB 接続を受ける純粋関数群を採用。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加：
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する `set_process_priority(level)`。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity(cpu_count)`。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制約 / 注意点
- .env の自動読み込みはプロジェクトルートが特定できない場合スキップされる（CWD に依存せずパッケージ配置後も安全に動作する設計）。
- process priority / cpu affinity の設定は権限や OS によって失敗する可能性があり、その場合はログで警告してスキップする。
- portfolio.position_sizing: lot_size は現状グローバルで共通の値（デフォルト 100）。将来的な拡張として銘柄ごとの lot_map をサポート予定（コード内コメントあり）。
- Paper Trading と本番 DB は分離設計を採用しているが、設定ミスにより同一 DB を参照するとデータが混在する可能性があるため、`SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` の設定に注意してください。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップする（警告出力）。YAML の厳密検証を行うには PyYAML を導入してください。

### セキュリティ (Security)
- なし（初回リリース）

---

（必要に応じて今後の変更はここに追記してください。）
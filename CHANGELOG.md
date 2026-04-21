# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。  

最新変更: 2026-04-21

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初回リリース。以下の主要コンポーネントと機能を追加しました。

### Added
- 基本パッケージ情報
  - `kabusys` パッケージを追加。バージョン `0.1.0` を設定。

- 設定管理
  - `kabusys.config.Settings`：環境変数/.env からの設定読み込みを行う設定クラスを追加。
    - 自動 .env ロード機能（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
    - `.env` / `.env.local` の読み込み順序、OS 環境変数の保護機構を実装。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境種別 等）。
    - 入力検証（`PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` 等）。

- 設定ユーティリティ
  - `kabusys.config_setup`：.env を対話式に生成・更新するウィザード CLI を追加。
    - 対話的プロンプト、既存 .env の読み込み、秘密項目のマスク表示、書き込み機能。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml 存在チェック、`--strict` モード等。
    - PyYAML 未導入時には YAML 検証をスキップして警告を出力。

- 実行/監視エントリポイント
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定（起動直後）。
    - Paper Trading 環境では専用の SQLite (`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`) を使用して本番 DB と分離。
    - Broker クライアントの生成（`BrokerClientFactory`）、OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンをバックグラウンドスレッドで実行し、プロジェクトルートの stop フラグ (`data/stop_requested.flag`) を監視して安全停止。
    - 実行 PID ファイル (`data/execution.pid`) の設定サポート。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60秒、無効値はデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番の sqlite_path を使用（監視は本番データを参照する設計）。
    - stop フラグファイルを検出するとループを終了。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を参照して監視テーブルの冪等な初期化を行う（`run_execution`/`run_monitoring` で利用）。

- ロギング/プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でのファイル出力をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_DIR / LOG_LEVEL の環境変数を尊重。
  - `kabusys.utils.process_priority`：
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 利用）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を追加。
    - 権限不足等で設定できない場合は警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（スコア降順、タイブレークに signal_rank）関数 `select_candidates`。
    - 等ウェイト `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコア 0 の場合は等ウェイトにフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限を適用する `apply_sector_cap`（売却予定銘柄の除外、unknown セクター扱いの挙動記載）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear 対応、未知系はフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - position size 算出ロジック `calc_position_sizes` を追加（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer の考慮、残余分の再配分アルゴリズムを実装。
    - リスクベース算出における stop_loss_pct / risk_pct の使用。

- リサーチ（部分実装）
  - `kabusys.research.factor_research`：
    - DuckDB 上の `prices_daily` / `raw_financials` を参照してモメンタム等のファクターを計算する設計を追加（モメンタム計算等の定義と定数を導入、関数の骨組みを実装開始）。一部実装途中（ファイル末尾で切れている箇所あり）。

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB は `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで上書き可能。
    - P95 の計算、NULL/データ欠損時の表示や例外時の保護を実装。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Notes / 安全設計と運用上の注意
- Paper Trading は本番 DB と完全に分離する設計（`paper_sqlite_path`）。本番口座の誤操作を防止。
- 監視ループ・実行エンジンは stop フラグファイル（`data/stop_requested.flag`）を監視して外部からの安全停止をサポート。
- 本番向け設定 (`KABUSYS_ENV=live`) の場合は追加の警告チェック（LINE 通知設定未設定や Kill Switch 設定）を行う。
- process priority / CPU affinity の設定はプラットフォーム依存で失敗する可能性があり、失敗時は警告を出して継続する。

---

今後の予定（想定）
- research モジュールのファクター計算の完遂（calc_momentum の実装完了など）
- ExecutionEngine / Broker 実装の拡充と e2e テスト
- 単体テスト・CI 設定の追加
- ドキュメント（PortfolioConstruction.md 等）の参照リンクやサンプル .env の整備

もし特定の変更点（ファイル追加/修正・バグ修正等）について詳細な Changelog 記述が必要であれば、対象のコミット差分や目的を教えてください。さらに詳細なリリースノートを作成します。
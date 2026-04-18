# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  

既存バージョン: __version__ = 0.1.0

---

## [Unreleased]

（現在の差分はありません）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム KabuSys の核となるユーティリティ群、実行/監視エントリポイント、ポートフォリオ構築ロジック、設定管理ツール、および検証・解析ツールを実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールの公開 API を整理（kabusys.portfolio のエクスポートなど）。

- 設定・環境管理
  - Settings クラスを実装し、環境変数経由で設定値を取得する仕組みを提供。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、ログレベル、KABUSYS_ENV 等をサポート。
    - PAPER_FILL_MODE の妥当性チェック（"instant" / "partial" / "never" / "reject"）。
    - KABUSYS_ENV の有効値検証（development / paper_trading / live）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env と .env.local を読み込み、OS 環境変数を保護する挙動を採用。
    - .env ファイルの行解析で export 形式、クォート、エスケープ、インラインコメント等に対応。

- 設定支援 CLI
  - 対話式ウィザードで .env を作成・更新する `kabusys.config_setup` を実装。
    - J-Quants / kabuステーション / DB / LINE 設定など主要項目を対話的に入力可能。
    - シークレット項目はマスク表示、デフォルト値や選択肢サポート、保存前の確認を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）などを検査。
  - --strict オプションで警告を失敗扱いにできる。

- 実行・監視
  - 実行エンジン起動スクリプト `run_execution.py` を実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory を使って本番/Mock ブローカークライアントを切り替え可能。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立てとエンジン起動フローを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理、デーモンスレッドでの実行と安全停止処理を備える。
  - 監視ループ起動スクリプト `run_monitoring.py` を実装。
    - SystemMonitor の一回チェックループを定期実行（デフォルト 60 秒）。MONITOR_POLL_INTERVAL 環境変数で上書き可能（無効値のフォールバック処理あり）。
    - 監視は環境にかかわらず本番の sqlite_path を利用して監視テーブルを初期化。
    - 停止フラグの検出と正常終了、例外時のログ出力を実装。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗などのフォールバック処理を実装。
  - `kabusys.utils.process_priority` を実装。
    - psutil を用いて Windows / POSIX に跨るプロセス優先度（high/normal/low）設定を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対する安全なフォールバック処理を実装。

- ポートフォリオ構築
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順・タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全0時は等分にフォールバック）。
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中上限を適用し、超過セクターの候補を除外。
    - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に応じた資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応し、単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積）対応を実装。

- リサーチ / ツール
  - factor_research（kabusys.research.factor_research）の骨組みを追加（モメンタム等の計算を計画）。
  - Paper Trading 用検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を実装。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し、PASS/FAIL 判定（閾値で判定）を行う。
    - 日付フィルタ、DB パス選択（--db / 環境変数）と各種エラー耐性を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- シークレット環境変数（J-Quants トークン、kabu API パスワード、LINE トークンなど）は .env の書き出し時にマスクや Secret 扱いで取り扱う手順を用意。

### Notes / Implementation details
- .env の自動ロードはプロジェクトルートの検出に依存しており、検出できない場合は自動ロードをスキップします。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- run_monitoring は MONITOR_POLL_INTERVAL が無効（非正整数や 0 以下）でも安全にデフォルト 60 秒にフォールバックします。
- run_execution は paper_trading と live を明確に分離し、paper_trading 時は Mock ブローカー & 専用 DB を利用して実際の発注を行わない運用を保証します。
- ログ設定は既存ハンドラの二重登録を防ぐため、セットアップ時に既存ハンドラをクリアして再設定します。
- process_priority と set_cpu_affinity は権限不足や未対応環境で警告を出して安全に続行する設計です。

---

今後の予定（例）
- factor_research の各ファクター実装完了（Momentum / Value / Volatility / Liquidity）。
- Strategy モジュール（シグナル生成・フィルタ）とバックテストツールの追加。
- ブローカークライアントの詳細実装、取引ロジックの拡充とより詳細なテストカバレッジの追加。

もし CHANGELOG に追加してほしい点や、記載の修正希望があればお知らせください。
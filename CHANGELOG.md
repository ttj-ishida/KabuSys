# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - Settings クラス（kabusys.config）を追加。
    - 環境変数からの設定取得を提供（J-Quants / kabuステーション / LINE / DB / 監視閾値 等）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）。
    - デフォルトのパス: DuckDB (`data/kabusys.duckdb`)、SQLite (`data/monitoring.db`)、paper trading DB (`data/paper_trading.db`) 等。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パース実装: export プレフィックス、クォート内のエスケープ、インラインコメント処理に対応。

- 環境設定ウィザード
  - `kabusys.config_setup` に対話式ウィザードを追加。
    - .env の初期作成・更新を補助（対話入力、既存値の再利用、シークレット扱い）。
    - 出力テンプレートを .env に書き込み。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - 本番環境 (live) 向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を失敗扱いにする機能。

- 実行/監視エントリポイント
  - `run_execution`（ExecutionEngine 起動スクリプト）
    - settings に基づく DB 接続（paper_trading 環境では paper_trading 専用 SQLite を使用して本番 DB と完全分離）。
    - BrokerClientFactory を介したブローカークライアント生成（KABUSYS_ENV=paper_trading 時に MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine の起動・デーモンスレッド管理、停止フラグ検出（data/stop_requested.flag）、PID ファイル指定。
  - `run_monitoring`（SystemMonitor ポーリングループ起動スクリプト）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、無効値は警告してフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 監視 DB 初期化（init_monitoring_db）、duckdb 接続の確保、stop フラグ検出、例外耐性付きループ。

- 監視/運用ユーティリティ
  - `kabusys.utils.process_priority`
    - プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）。
    - CPU アフィニティ設定（set_cpu_affinity）。
    - Windows / POSIX(nice) の差異を吸収し、アクセス権限エラー等は警告して安全にスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順で候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重みの計算（スコア全0時は等分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率に基づく候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元株丸め、per-stock 上限・aggregate cap、スケールダウンロジック（remainder に基づく再配分）などを実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB を使用し prices_daily テーブル参照）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比等を計算するクエリ（データ不足時は None を扱う）。
    - 大規模データは DuckDB(SQL) で集計する設計。

- 運用レポートツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - デフォルト DB: data/paper_trading.db（環境変数/PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等。
    - 判定基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）対応、DB 存在チェック、SQL 実行時の OperationalError に対するグレースフルなフォールバック。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / Implementation details
- .env のパースはシンプルな実装ながら、シングル/ダブルクォート内のバックスラッシュエスケープや export 形式、インラインコメント処理に対応しており、テストや配布後の利用を想定した堅牢化を行っています。
- process priority / cpu affinity は権限不足や未対応 OS の場合に警告を出して継続する設計です（運用環境での致命的不整合を避けるため）。
- Paper Trading と Live の DB 分離を明確にしており、誤って本番 DB にテストデータを書き込まない運用を支援します。
- Portfolio / PositionSizing の関数群は純粋関数として設計され、外部 DB 参照を行わずテスト容易性を高めています。

---

(今後の変更はこのファイルに逐次追加してください。)
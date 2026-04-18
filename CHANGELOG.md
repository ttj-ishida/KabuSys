# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ/バージョンはリポジトリ内の `kabusys.__version__`（現行: 0.1.0）に基づいています。

※日付はこのリリース作成日です。

## [Unreleased]

（現時点のブランチに未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回リリース。本リポジトリに含まれる主要機能と実装の要点は以下のとおりです。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV による Paper Trading 分離をサポート（paper_trading 時は専用の SQLite DB を使用）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等のコンポーネントを組み立て、別スレッドでエンジンを実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）の取り扱い。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループのエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は本番用の sqlite_path を常に使用（環境に依存しない）。
- 設定管理・ユーティリティ
  - config.py
    - 環境変数のラッパー `Settings` を実装。各種既定値、検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供。
    - プロジェクトルート自動検出（.git / pyproject.toml）を行い、.env/.env.local の自動読み込みを実施（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - `settings` 単一インスタンスをエクスポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の設定項目をサポート。
  - validate_config.py
    - .env や config/*.yaml の起動前検証ツール。
    - 必須環境変数、KABUSYS_ENV、DB パス、YAML パース（PyYAML があれば）等のチェック。
    - `--strict` オプションで警告を FAIL 扱いにする機能を提供。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップ関数 `setup_logging` を実装。
    - LOG_DIR が作成できない場合はファイル出力をスキップしてコンソール出力のみ継続するフォールバックあり。
  - utils/process_priority.py
    - Windows / POSIX(Linux/macOS 等) を吸収するプロセス優先度設定 (`set_process_priority`) と CPU affinity 設定 (`set_cpu_affinity`) を提供。
    - 権限不足や未対応 OS の場合は安全にフォールバックして警告を出力。
- ポートフォリオ構築ライブラリ（純関数・DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点時は signal_rank）と等配分・スコア加重配分の実装。
  - portfolio/position_sizing.py
    - 重み・候補・価格情報から銘柄ごとの発注株数を算出する主要ロジックを実装（allocation_method: risk_based / equal / score）。
    - aggregate cap によるスケールダウン、単元株（lot_size）丸め、手数料・スリッページのバッファ考慮などに対応。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - レジーム: bull/neutral/bear のマップと未知レジームへのフォールバック。
  - portfolio/__init__.py で上記関数を公開。
- 研究・分析（DuckDB ベース）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールを実装（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（モジュール設計と主要定数を実装）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB からシステム安定性・注文成功率・レイテンシ等を集計し、PASS/FAIL 形式の検証レポートを標準出力に生成。
    - P95 レイテンシ計算、閾値による判定（稼働率 / 成功率 / 送信率 / P95）を実装。
    - オプション: --from / --to / --db に対応。環境変数 `PAPER_TRADING_SQLITE_PATH` を優先して参照。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Documentation
- 各モジュールに日本語ドキュメンテーション文字列（docstring）を整備。CLI の使い方や各種環境変数について明記。

### Notes / Design Decisions
- 環境変数の .env 読み込み:
  - 読み込み順は OS 環境変数 > .env.local > .env（.env.local が .env を上書き）。
  - `.env` のパースはクォートやバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
- Paper Trading は本番 DB と完全分離（デフォルト `data/paper_trading.db`）。
- 監視（monitoring）関連は env にかかわらず本番の sqlite_path を利用（監視情報は本番 DB を対象とする想定）。
- ログは標準出力を stdout に統一し、ファイル出力はオプションで行う設計。これにより cron 等の運用で stdout/stderr を一元管理しやすくしている。
- process_priority / cpu_affinity の設定はプラットフォームや権限に依存するため、安全にフォールバックする実装。

### Known limitations / TODOs
- position_sizing.calc_position_sizes: 銘柄ごとの単元株数(lot_size) は現在全銘柄共通のパラメタであり、将来的に銘柄別の lot_map を受け取る拡張が想定されている（TODO コメントあり）。
- research/factor_research.py はファクター設計に基づく関数群を含むが、実運用上の細部（スキャン範囲や欠損値処理等）は継続してテスト/チューニングが必要。
- 本リリースでは API クライアント等の外部依存コンポーネント（BrokerClient 等）はファクトリ経由で生成される設計だが、実際のブローカー固有実装やモックの細部は別パッケージ／モジュールで提供される前提。

### Security
- 機密値（API トークン等）は .env にて管理する想定。`.env` は Git へコミットしない旨を config_setup のヘッダに明記。

---

今後のリリースでは以下を優先して改善予定です:
- 単体テストの拡充（position sizing / risk adjustment / portfolio builder / factor calc）
- BrokerClient のインターフェース安定化とモックの整備
- モニタリングと通知（LINE）ワークフローの統合テスト
- DuckDB スキーマ管理・マイグレーションの仕組み整備

以上。
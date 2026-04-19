# CHANGELOG

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 項目はセクション（Added / Changed / Fixed / Removed / Security）に分類しています。
- 各リリースはタグ名（バージョン）と日付を付記しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初回公開リリース。日本株自動売買システム KabuSys の基本機能群を提供します。

### Added
- パッケージ初期版を追加（__version__ = "0.1.0"）。
- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するランナー。
    - スレッドで engine.run_session を実行し、外部停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - pid ファイル（data/execution.pid）管理をサポート。
    - DuckDB を分析用に併用（設定でパス指定可能）。
    - RiskManager のデフォルト設定値を組み込み（例: max_position_pct=0.20, max_utilization=0.80 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するランナー。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（プロジェクト/data/stop_requested.flag）検出でループ終了。
- 環境設定 / 管理
  - config.py
    - .env ファイル自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 複雑な .env 行のパース対応（export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメント規則）。
    - Settings クラスを導入してアプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、各種監視閾値、KABUSYS_ENV 判定など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援。
    - シークレット項目はマスク表示、選択肢やデフォルト提示、保存前の確認プロンプトあり。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース検証（PyYAML 未インストール時は警告）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセス設定ユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング設定ユーティリティを追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - アクセス権限不足等の例外は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコア全体が 0 の場合のフォールバックロジック（等分配）あり。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有比率が閾値超過のセクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マップ、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を追加。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer を使った保守的見積り、残余キャッシュに基づく再配分ロジックあり。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（avg/max/P95）を集計・判定。
    - デフォルト閾値（稼働率 >=99%、Fill >=90%、Send >=95%、P95 <=200 ms）を採用。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。

### Changed
- なし（初回リリースのため変更履歴はなし）。

### Fixed
- なし（初回リリース）。

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックし、time.sleep へ安全に渡すよう設計されています。
- run_execution は paper_trading モードで本番 DB と完全分離された SQLite を使用するため、ペーパートレード検証時の誤操作リスクを低減します。
- .env 読み込みは OS 環境変数を保護（protected）しつつ .env.local で上書き可能とする優先度ルールを採用しています。
- ログの StreamHandler は stdout を使用（stderr ではない）: 外部スケジューラやリダイレクト運用を考慮した挙動です。
- DuckDB は分析用途（prices_daily 等）向けに採用。research/factor_research.py はファクター計算（Momentum 等）を実装する設計で着手されています（モジュールは一部実装中）。

---

今後の予定（例）
- ExecutionEngine / SystemMonitor のさらに詳細なエラーハンドリングとメトリクス拡張
- factor_research の完全実装（Value / Volatility / Liquidity 等）
- strategy 実装・バックテストツールの追加
- 単体テスト整備および CI ワークフローの導入

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートは必要に応じて調整してください。）
# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離する設計。  
    - 起動時にプロセス優先度を "high" に設定し、pid ファイル（data/execution.pid）を利用。停止は data/stop_requested.flag で制御。  
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立ててエンジンをスレッドで実行。  
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み、初期ポートフォリオ値はブローカーの available cash を用いる。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視 DB は環境にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用。停止は data/stop_requested.flag で制御。  

- 設定管理
  - config.py: 環境変数 / .env 読み込みと Settings クラスを追加。  
    - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - 強力な .env パーサ実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。  
    - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DuckDB/SQLite パス / paper trading 関連 / 監視閾値 / KABUSYS_ENV / LOG_LEVEL 等）。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の値検証を実施。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。  
    - 秘匿項目はマスク表示、既存 .env の読み込みと Enter で既存値再利用、選択肢チェック、最終確認後にテンプレート形式で .env を書き出す。  

- 設定検証
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須/任意の環境変数チェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill Switch の注意喚起）。  
    - --strict オプションで警告を FAIL 扱いにできる。

- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成ツールを追加。  
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を集計し、定義済み閾値に対する PASS/FAIL を判定。  
    - --from / --to / --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB を指定可能。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。score が全て 0 の場合は等重にフォールバック。  
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を追加（regime マップ: bull/neutral/bear。未知のレジームは警告して 1.0 でフォールバック）。  
  - portfolio/position_sizing.py: 発注株数決定ロジックを追加。  
    - allocation_method: "risk_based" / "equal" / "score" に対応。  
    - lot_size（単元株）丸め、1 銘柄上限・集約上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積もり、端数配分ロジックを実装。  

- 研究モジュール
  - research/factor_research.py: DuckDB 接続を利用したファクター計算基盤を追加（Momentum / Value / Volatility / Liquidity を想定）。（モジュールは DuckDB の prices_daily / raw_financials テーブルを参照して計算する設計）

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。  
    - LOG_LEVEL / LOG_DIR 環境変数と引数に基づく解決順を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil ベース）。  
    - Windows / POSIX（Linux, macOS, FreeBSD）差分吸収。失敗時は警告を出してスキップ。  

- パッケージ情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Notes / 注意事項
- 本リリースでは監視テーブル初期化関数 init_monitoring_db や SystemMonitor / ExecutionEngine 本体の詳細実装は別モジュールに分離されています（起動スクリプトはそれらを呼び出す形）。実運用前に各コンポーネントの設定・挙動確認を推奨します。  
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のトップに注意書きあり）。  
- KABUSYS_ENV=live で起動する際は validate_config による事前検証と LINE 通知設定の確認を強く推奨します。  

<!-- バージョン管理のため、今後の変更はこのファイルに追記してください。 -->
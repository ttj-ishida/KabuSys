# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグ付けはバージョン番号と日付（YYYY-MM-DD）で行っています。

## [Unreleased]

- 開発中の変更はここに記載されます。

## [0.1.0] - 2026-04-18

### Added
- 基本機能の初期実装を追加（初回リリース）。
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用する。起動時にプロセス優先度を"high"に設定し、停止フラグ（data/stop_requested.flag）および PID ファイル管理を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定・環境管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートの検出は .git / pyproject.toml ベース）。.env/.env.local の読み込み順・上書きルール、複数の設定プロパティ（DB パス、API トークン、監視閾値、環境種別等）を提供。PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の検証を実装。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加（質問項目の定義、既存値読み込み、保存機能）。秘密鍵のマスク表示や保存前の確認を実装。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証、live 環境向けの追加警告等を実施。--strict オプションで警告も失敗扱いにできる。
- ロギング・ユーティリティを追加
  - utils/logging_setup.py: ルートロガー設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ自動作成、ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
- プロセス制御ユーティリティを追加
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定を実装。アクセス拒否等の失敗は警告出力してスキップ。
- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額配分、スコア加重配分を実装。スコア全ゼロ時のフォールバック（等配分）を警告付きで実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告のうえフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、ポートフォリオ全体の aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュによる端数配分ロジックを実装。
  - portfolio/__init__.py: 上記関数群の公開 API をまとめてエクスポート。
- リサーチ（ファクター計算）の骨組みを追加
  - research/factor_research.py: モメンタム・MA200 乖離・ATR・出来高等の算出設計を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針。計算窓や定数を定義（例: 1M/3M/6M、MA200、ATR 20 日等）。（一部実装は継続中）
- ツール群を追加
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。日付範囲フィルタ、DB パスの指定（引数 or 環境変数）に対応。
- 監視 DB 初期化ヘルパー導入
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを起動時に行うことで、監視テーブルが存在しない場合の自動作成（冪等）を保証。
- パッケージメタデータ
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

注記:
- 本 CHANGELOG はソースコードから推定して作成しています。実際のリリースノート作成時は変更差分やコミット履歴に基づいて追記・修正してください。
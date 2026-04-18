# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初期リリースを記録しています。

[Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。プロセス優先度を設定し、スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視モジュールは環境に関わらず本番 sqlite_path を使用する挙動を実装。
- 設定管理
  - config.py: 環境変数／.env 自動読み込み機能を追加（プロジェクトルート自動検出: .git / pyproject.toml）。.env と .env.local の読み込み順序、既存 OS 環境変数を保護する仕組み（protected）を実装。
  - .env パース機能を実装。`export KEY=val` 形式、クォート文字列とバックスラッシュエスケープ、インラインコメントの処理をサポート。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得（DB パス、API トークン、paper_trading 用 DB パス、監視閾値、環境判定等）。
- 設定支援ツール・検証
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を追加。シークレット項目のマスクや既存値の再利用、保存前確認を実装。
  - validate_config.py: .env と config/*.yaml（存在する場合）の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや YAML パースチェック、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションを実装（警告を FAIL 扱いにできる）。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保管）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux, Darwin, FreeBSD） を吸収し、設定失敗時は警告出力で安全にフォールバック。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック挙動を定義。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method による "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer（手数料・スリッページ見積）を考慮した aggregate cap スケーリング、残差処理（fractional remainder に基づく追加配分）を実装。
- 研究・分析ユーティリティ（開始実装）
  - research/factor_research.py: Momentum 等のファクター計算モジュールの枠組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。モメンタム・MA200 乖離・ATR 等の定義と計算方針を実装（関数群の実装途中。設計ドキュメントに基づく）。
- ツール類
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH の指定をサポート。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定する。既定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を定義。
- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定。主要サブパッケージを __all__ で公開。

### Changed
- なし（初回リリースのため過去からの変更はありません）。

### Fixed
- なし（初回リリース）。

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env の自動上書きを防止）。また config_setup において .env を生成する際にシークレット項目はマスク表示。

### Notes / Usage highlights
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 SQLite DB と分離します。Execution 起動時は settings.is_paper に応じて DB パスが切り替わります。
- 監視（run_monitoring.py）は環境に関わらず settings.sqlite_path（本番監視 DB）を参照します（設計上モニタは常に本番監視 DB に書き込む想定）。
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- process_priority.set_process_priority("high") は各起動スクリプトの冒頭で呼ばれます。設定に失敗してもログ警告で安全に継続します。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップし stdout のみで継続します。
- validate_config.py の --strict を使うと警告も失敗扱い（exit code 1）になります。CI 等での事前チェックに利用可能です。
- position_sizing の aggregate スケーリングは lot_size 単位で丸め、残余キャッシュで残差分を上位順に追加配分するアルゴリズムを採用しています。

### Breaking Changes
- なし（初回リリース）。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター集約・正規化・出力フォーマット）。
- ExecutionEngine / SystemMonitor のさらなるテストカバレッジ追加。
- 銘柄別単元サイズ（lot_size）のマスタ対応、手数料・スリッページの詳細化。
- monitoring_db, execution, risk 等サブモジュールの詳細実装およびドキュメント追加。

リリースに関する不明点や追記希望があれば教えてください。必要に応じて変更履歴を詳細化します。
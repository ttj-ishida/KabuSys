# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-25
初回リリース。主要な機能・CLI・ユーティリティ群を追加。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレーディング用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient 経由で完全に本番 DB から分離。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を使用した安全な起動／停止制御。
  - run_monitoring.py
    - システム監視ループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視（monitoring）処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して状態を記録。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定関連
  - config.py
    - .env ファイル自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパース処理を強化（export プレフィックス、クォート内エスケープ、インラインコメント処理等対応）。
    - Settings クラスを追加し、環境変数の取得・検証を集中管理（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境判定など）。
    - PAPER_FILL_MODE の検証、paper_trading 用 DB パス、PID / KILL フラグ等のプロパティを提供。
- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新できる CLI を追加。
    - J-Quants / kabu API の秘密値はシークレット入力として扱い、既存値は Enter で再利用可能。
    - 書き込み前に設定内容を確認し、承認後 .env を保存。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在）チェック、YAML パース（PyYAML がある場合）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み取り、稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計するレポート生成スクリプトを追加。
    - しきい値に基づく PASS/FAIL 判定を出力。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 (select_candidates)。
    - 等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して候補を除外する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知値は警告してフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に応じたスケーリング）、コストバッファを考慮した安全な配分アルゴリズムを実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を提供。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。
    - LOG_LEVEL / LOG_DIR の環境変数優先解決、既存ハンドラのクリア、ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS の差を吸収してプロセス優先度設定 set_process_priority を実装（high/normal/low）。
    - CPU affinity 設定 set_cpu_affinity を追加（最初の N コアにピン留め）。
    - 権限不足や未対応プラットフォームでは安全にスキップして警告を出力。
- 研究用モジュール（骨格）
  - research/factor_research.py
    - prices_daily / raw_financials を用いたファクター計算（モメンタム、MA、ATR、出来高指標等）を行う設計を追加。DuckDB 接続を受け取り純粋関数で計算する方針と関連定数を定義（関数群は実装途中の箇所あり）。
- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ にエクスポート。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Removed
- (初回リリースのため該当なし)

### Security
- 環境変数読み込み周りで秘密情報の取り扱いに注意（.env を絶対に Git にコミットしない旨を config_setup の生成ファイルに明示）。

Notes:
- run_monitoring/run_execution 等の起動スクリプトは、外部の broker/client 実装や監視テーブル等に依存します。実運用前に env / config/*.yaml / DB スキーマ の検証を行ってください（`python -m kabusys.validate_config` を推奨）。
- 一部モジュール（research/factor_research の一部関数など）は実装途中・拡張余地あり。今後のリリースで追加実装・性能改善・テスト拡充を予定しています。
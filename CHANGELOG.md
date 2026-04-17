# Changelog

すべての注目すべき変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期リリースを追加。
- 環境設定・管理
  - Settings クラス（kabusys.config）を導入し、アプリ設定を環境変数から取得する統一インターフェースを提供。
  - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）を追加。OS 環境変数は保護され、上書きされない仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメント処理を実装）。
  - config_setup CLI（kabusys.config_setup）を追加。対話式ウィザードで .env の初期作成・更新を行う。シークレット項目のマスク表示、デフォルト・選択肢説明、保存前確認を実装。
- 設定検証ツール
  - validate_config CLI（kabusys.validate_config）を追加。必須環境変数やパス、config/*.yaml の存在・パース検証を実施。--strict フラグで警告も失敗扱いにできる。
  - PyYAML が未インストールの場合は YAML検証をスキップし警告を出す。
- 実行 / 監視プロセス起動スクリプト
  - run_execution（kabusys.run_execution）を追加。ExecutionEngine の起動フローを実装（ブローカ生成、リポジトリ/OrderManager/RiskManager/Reconciler 組み立て、スレッド実行、停止フラグ監視）。
    - ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を組み込み。
    - エンジン停止制御は data/stop_requested.flag と data/execution.pid を利用。
  - run_monitoring（kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ起動を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明確化。
    - 停止フラグ（data/stop_requested.flag）によるループ終了処理を実装。
    - check_once() 実行時の例外はログ出力して次ポーリングへ継続する安全策を採用。
  - どちらの起動スクリプトも起動直後にプロセス優先度を "high" に設定する処理を組み込み（kabusys.utils.process_priority.set_process_priority を使用）。
- プロセス制御ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）を追加。Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を設定する set_cpu_affinity も実装。権限不足や未対応 OS の場合は警告してスキップ。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio_builder: 候補選定 select_candidates、等金額/スコア加重重み calc_equal_weights / calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment: セクター集中制限 apply_sector_cap（当日売却予定除外、"unknown" セクターは制限除外）と市場レジームに対応する乗数 calc_regime_multiplier（bull/neutral/bear → 1.0/0.7/0.3）を実装。未知レジームは 1.0 でフォールバック。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）、max_position_pct/max_utilization、cost_buffer（手数料・スリッページ見積）や aggregate cap のスケーリングロジック、端数処理（lot 単位）を実装。
  - portfolio パッケージのエクスポートを整理。
- リサーチ / ファクター計算
  - research.factor_research を追加。DuckDB 接続を受け取り、prices_daily / raw_financials を用いて Momentum / Volatility / Liquidity / Value 系ファクターを計算するための関数群（例: calc_momentum, calc_volatility）を実装。ウィンドウサイズやスキャン範囲は定数化（200日移動平均、ATR 20日 等）。欠損データ時の安全な NULL 処理を行う。
- ツール
  - tools.paper_verification_report を追加。Paper Trading の SQLite（デフォルト data/paper_trading.db）から集計を行い、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99.0%、注文成立率 >= 90%、P95 <= 200ms）。
    - P95 の計算を内部で実装（空データは N/A）。
    - 日付範囲フィルタ（--from / --to）と --db オプションをサポート。

### Changed
- パッケージメタ情報としてバージョンを __version__ = "0.1.0" に設定。
- run_execution/run_monitoring の起動フローで監視用テーブルが存在することを保証するため init_monitoring_db を呼び出すようにした（冪等）。

### Fixed
- 環境変数パースの堅牢化により、.env 内のクォートやエスケープ、コメント解釈での誤動作を修正（export 形式対応等）。
- MONITOR_POLL_INTERVAL に不正な値（0 や非数）が設定された場合に time.sleep が例外を投げないように、デフォルトにフォールバックして警告を出す処理を追加。

### Notes / Dependencies
- DuckDB（duckdb パッケージ）を利用するコードが含まれるため、DuckDB ライブラリが必要です。
- プロセス優先度設定には psutil を使用します。psutil が存在しない、権限がない場合は優先度設定はスキップされます（警告）。
- YAML 検証は PyYAML に依存（インストールされていないと警告を出し該当検証をスキップ）。
- 本リリースでは .env を絶対にリポジトリにコミットしないことを推奨します（config_setup に注意書きあり）。

---

今後のリリース候補（例）
- より詳細なログ設定反映（Settings.log_level の活用）
- 銘柄ごとの lot_size マスタ化対応（position_sizing の拡張）
- 監視・実行の systemd / サービス化サポートの追加検討
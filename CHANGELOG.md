# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（src/kabusys 以下）の現在の実装内容から推測して作成しています。

全般:
- このリリースはパッケージの初期公開相当（機能群のまとまった提供）を想定しています。
- コマンドラインツール、環境設定/検証ユーティリティ、監視/実行用のランナー、ポートフォリオ構築・ポジション算出ロジック、ファクター計算、ユーティリティ関数群などを含みます。
- バイナリ互換性や外部 API の詳細実装（ブローカーなど）はファクトリやインターフェースで抽象化されています。

## [Unreleased]
- （将来の差分用に予約）

## [0.1.0] - 2026-04-17
初回公開リリース（推測）。以下の主要機能と実装を含みます。

Added
- 基本パッケージ情報
  - パッケージバージョン: __version__ = "0.1.0"
- 環境設定/読み込み
  - Settings クラスを追加（環境変数から各種設定を取得）
  - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）
  - .env パーサーはシングル/ダブルクォートやエスケープ、コメント処理をサポート
  - 環境変数読み込み順: OS 環境 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション
  - 必須環境変数チェック用 _require() 実装
  - PAPER_FILL_MODE/SQLITE/DUCKDB 等のデフォルトパスと検証ロジック

- 環境設定ウィザード
  - config_setup.py: 対話式ウィザードで .env の作成・更新を支援
  - 保存前の確認、シークレットマスク表示、既存 .env の読み込み再利用に対応

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の存在・基本整合性チェック
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば内容検証）
  - --strict モードで警告を FAIL 扱いにできる

- 実行ランナー / 監視ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプト（Thread ベースでセッションを実行）
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
    - BrokerClientFactory 経由でブローカークライアントを生成
    - RiskManager / OrderManager / Reconciler / OrderRepository 等の組み立てと ExecutionEngine 起動
    - data/execution.pid 管理、stop flag 検出で安全に停止
    - 起動時にプロセス優先度を "high" に設定
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒、無効値時にフォールバック）
    - monitoring は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化）
    - stop flag 検出、例外ログ、リソースクローズ処理

- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な作成を保証

- ポートフォリオ構築・ポジション算出（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順選択（タイブレーク: signal_rank）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存ポジション時価を算出し上限超過セクターから候補除外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull|neutral|bear のマッピング、未知は 1.0 にフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算
    - 単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り
    - risk_based: 損切り幅と許容リスク率からベース株数計算
    - スケーリング時に残差の大きい順に lot 単位で追加配分するロジックを実装

- リサーチ / ファクター計算
  - research.factor_research
    - DuckDB を使ったファクター計算モジュール（prices_daily / raw_financials テーブル参照）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率（部分窓でも算出）
    - 計算用のスキャン期間や窓幅は定数で管理

- ツール
  - tools.paper_verification_report
    - ペーパートレード DB を解析して検証レポートを生成（稼働率、注文成功率、送信率、P95 レイテンシ等）
    - 基準値（uptime 99%、fill_rate 90%、send_rate 95%、P95 <= 200ms）に基づく PASS/FAIL 判定
    - 日付フィルタ、DB パスの CLI オプション・環境変数対応

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収する抽象化
    - set_cpu_affinity(cpu_count): 指定コア数に固定（未指定時は noop）
    - アクセス権限や未対応 OS 時のフォールバック/警告処理

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）
  - ただしロバスト性を高めるため、.env 読み込み失敗時の警告、MONITOR_POLL_INTERVAL の不正値警告、psutil 呼び出し時の AccessDenied/NotImplemented 例外捕捉などのフォールバック処理を多数実装

Security
- 機密値（API トークン・パスワード）入力時にウィザードでマスク表示、.env ファイルは "絶対に Git にコミットしないこと" をドキュメント化

Notes / Usage highlights
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- 環境分離:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離
  - Monitoring はコメントに基づき「環境にかかわらず本番 sqlite_path を使用」する実装注記あり
- 停止/制御:
  - data/stop_requested.flag および data/execution.pid などのファイルベースの stop/pid 管理により外部から停止指示が可能

Acknowledgements / Limitations
- ブローカークライアントや ExecutionEngine の内部実装、Strategy モデルの詳細、DB スキーマ（monitoring_db の詳細定義など）は本 CHANGELOG では推測の範囲に留めています。
- 実際の動作には外部依存（psutil、duckdb、yaml など）が必要です。必要モジュールがない場合は警告やスキップ動作があります。

(注) 本 CHANGELOG は提示されたソースコードの内容から推測して作成したものであり、実際のリリースノートとは異なる場合があります。
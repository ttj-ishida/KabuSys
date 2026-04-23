# CHANGELOG

すべての注目すべき変更点を記録します（Keep a Changelog 準拠）。  
このファイルはソースコードの内容から推測して作成しています。

注意: 日付は推定値です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装（初回リリース）。
- 環境設定 / 設定管理
  - Settings クラスによる環境変数ラッパーを追加。J-Quants / kabu API / DB パス /ログ・監視閾値等のプロパティを提供。
  - 環境変数自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - .env ファイルのパースを独自実装（"export " プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装。.env の初期作成・更新を支援する。
  - 秘匿項目はマスク表示、デフォルト/既存値再利用機能を提供。
- 設定検証 CLI
  - validate_config.py に .env や config/*.yaml の起動前検証ツールを追加。
  - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの存在確認（親ディレクトリチェック）、YAML のパースチェック（PyYAML 未導入時は警告）などを実施。
  - --strict オプションで警告を失敗として扱うモードを提供。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を利用した安全な起動/停止フローを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB の一貫性確保）。
    - stop flag によるシャットダウンと KeyboardInterrupt のハンドリングを実装。
- 監視 DB 初期化
  - init_monitoring_db（監視用テーブルの冪等初期化）を呼ぶことで、起動時に監視テーブルの存在を保証。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、LOG_LEVEL/LOG_DIR の解決ルール、30 日分保持の設定などを備える。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）の差分を吸収。アクセス権限不足等で失敗した場合は警告ログを出してスキップ。
    - set_cpu_affinity により最初の N コアにプロセスをピン留めする機能を提供。
  - 起動スクリプトからは最初に set_process_priority("high") を呼び、優先度を上げる設計。
- ポートフォリオ構築モジュール
  - portfolio パッケージを追加。
    - portfolio_builder.py: 候補選定（スコア降順、同点は signal_rank でブレーク）、等金額配分、スコア加重配分（全銘柄スコア 0 の場合はフォールバック）を実装。
    - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
      - apply_sector_cap は sell_codes（当日売却予定）を考慮し、"unknown" セクターは上限適用しない挙動。
      - calc_regime_multiplier は bull/neutral/bear のマップを提供し、未知のレジームは警告のうえ 1.0 にフォールバック。
    - position_sizing.py: 株数決定ロジックを実装。
      - allocation_method に "risk_based"（リスクベース）および "equal"/"score" をサポート。
      - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を考慮した保守的見積り、残余配分の再配分ロジックなどを実装。
- 研究 / ファクター計算
  - research/factor_research.py を追加。DuckDB 接続から prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（モメンタム計算関数の実装開始を含む）。
- ツール群
  - tools/paper_verification_report.py を追加。ペーパートレード DB から検証レポートを生成する CLI。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 期間フィルタ（--from, --to）、各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ）を集計。
    - P95 などの統計計算および閾値による Pass/Fail 判定を実装。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- パッケージ初期化
  - kabusys.__init__ に __version__ = "0.1.0" を設定。主要サブパッケージを __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- シークレット値（トークン・パスワード）の .env 保存時はマスク表示や説明で注意喚起を追加（config_setup にて .env を絶対に Git にコミットしない旨を明記）。

---

参考: 各スクリプト・モジュールは CLI から直接実行可能（python -m kabusys.<module>）を想定したエントリポイントを持ち、起動時の安全シャットダウン（stop flag / kill flag / PID ファイル）やログ・DB 接続のクリーンアップ処理に配慮しています。

（この CHANGELOG はコードを読み取って推測した内容に基づくため、実際の変更履歴と異なる場合があります。）
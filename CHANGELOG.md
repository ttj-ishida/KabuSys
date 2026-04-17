# CHANGELOG

すべての非マイナー変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として設定。

- 設定・環境変数管理
  - Settings クラスを実装：環境変数から各種設定を取得する統一インタフェースを提供（J-Quants / kabuAPI / DB パス / PID / 監視閾値など）。
  - .env 自動ロード機能を実装（プロジェクトルート検出に .git / pyproject.toml を利用）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - 堅牢な .env パーサを実装：
    - export プレフィックス、シングル／ダブルクォート内のエスケープ、インラインコメント処理をサポート。
  - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）および PAPER_TRADING_SQLITE_PATH など Paper Trading 用設定を追加。
  - 環境判定プロパティ（is_live / is_paper / is_dev）を提供。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。
    - 各設定項目の説明表示、既存値の再利用、シークレットマスク表示、保存前確認を実装。
    - .env を生成する際に Git にコミットしない旨の注意コメントを付与。
  - validate_config: 起動前設定検証 CLI を追加。
    - 必須 / 任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML がない場合はパース検証をスキップして警告）。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告を失敗として扱うモードを提供。

- 実行スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading モードでは専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading の場合は MockBrokerClient 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと ExecutionEngine スレッド起動、停止フラグ（data/execution.pid, data/stop_requested.flag）に基づく安全停止を実装。
    - RiskManager のデフォルト設定を明記（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）。初期ポートフォリオ値は broker.get_available_cash() を使用。

  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックし警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を利用する（監視 DB として固定）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 例外発生時にログ出力して次ポーリングまで継続する堅牢性を確保。

- 監視・モニタリング
  - monitoring_db 初期化フックの呼び出しを各起動スクリプトに追加して、監視用テーブルの存在を保証（冪等）。

- DuckDB 統合
  - DuckDB パスを Settings で管理し、run_execution / run_monitoring で接続を確立。
  - research/factor_research モジュールで DuckDB 接続を受け取り、prices_daily テーブルを SQL で参照してファクター計算を行う設計を追加。
    - momentum（1M/3M/6M, MA200乖離）、volatility（ATR, 平均売買代金, 出来高比率）計算ロジックを実装（営業日ベースのウィンドウ処理、欠損データに対する None 戻り）。

- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数で副作用なし）。
    - portfolio_builder: シグナル選定（score 降順 + tie-break）、等比配分・スコア比配分（スコア合計が 0 の場合は等金額にフォールバック）。
    - position_sizing: position サイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。lot サイズ丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応、残差処理によるロット調整を実装。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく資金乗数（calc_regime_multiplier）を追加。未知レジームは警告後フォールバック。

- ユーティリティ
  - process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加（psutil を利用）。Windows / POSIX（Linux, Darwin, FreeBSD）での差分を吸収し、権限不足や未対応 OS では警告を出してスキップ。
  - CPU affinity 設定は最初の N コアに固定する機能を提供（引数の妥当性チェック含む）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 向け検証レポート生成スクリプトを追加。CLI 引数で期間指定（--from/--to）や DB パス指定（--db）が可能。
    - 指標:
      - 稼働率（uptime_pct）閾値: 99.0%
      - 注文成功率（fill_rate）閾値: 90.0%
      - 送信率（send_rate）閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - system_status / trade_logs / risk_logs テーブルから各種統計を集計し、Pass/Fail 判定を出力。P95 はカスタム計算実装。
    - DB が存在しない、またはテーブルがない場合に graceful に N/A を出力。

- パッケージエクスポート
  - kabusys.portfolio の __all__ を整備して主要関数を公開。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- .env ファイルの取り扱いに関する注意をドキュメント的に追加（config_setup にヘッダコメント、validate_config に注意喚起）。
- シークレット情報は CLI でマスク表示し、.env の Git 管理禁止を明記。

### Notes / Implementation details
- 設定のロード順序: OS 環境変数 > .env.local > .env（プロジェクトルートが自動検出できない場合は自動ロードをスキップ）。
- run_monitoring は監視 DB に対して常に Settings.sqlite_path（本番用）を使う設計。Paper Trading の監視は run_execution 側で paper_sqlite_path を使用して分離している。
- 各種機能は外部ライブラリ（psutil, duckdb, sqlite3, PyYAML 等）に依存。PyYAML が無い場合は YAML 検証をスキップして警告を出す。

---

将来的なリリースでは次のような項目を追記してください:
- バグ修正、性能改善、追加の診断メトリクス。
- strategy や execution の詳細アルゴリズム変更、テスト追加、ドキュメント強化。
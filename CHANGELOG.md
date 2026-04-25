# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

最新の変更は一番上に記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース。本リポジトリに含まれる主要機能・CLI・ユーティリティを実装しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定・管理
  - Settings クラスによる環境変数ベースの設定管理を実装（kabusys.config）。
    - デフォルト値や必須変数チェック、環境別フラグ（development / paper_trading / live）をサポート。
    - DB パス（DuckDB / SQLite）、PID/kill フラグ等の標準的な設定を提供。
    - PAPER_FILL_MODE 等の列挙的な検証を実装（不正値で例外）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出、.env / .env.local の読み込み、OS 環境変数保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- 対話式設定ウィザード CLI
  - `kabusys.config_setup`：対話式に .env を作成/更新するウィザードを実装。
  - .env の読み書きロジック、入力プロンプト、既存値の再利用、シークレットマスク表示などをサポート。

- 設定検証 CLI
  - `kabusys.validate_config`：.env や config/*.yaml の事前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML が存在する場合）など。
    - --strict モードで警告も失敗扱いにできる。

- 実行系起動スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動用スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てと ExecutionEngine の起動ロジックを提供。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行中の PID ファイル管理を考慮。

- 監視系起動スクリプト
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトフォールバック）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視データは共通 DB に記録）。
    - 停止フラグ検知でループ終了、例外捕捉とログ出力を実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：paper_trading 用 SQLite を解析して検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（avg/max/P95）などを集計。
    - Pass/Fail 判定の閾値を定義（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200ms）。
    - 日付範囲指定（--from/--to）や DB パス指定（--db / 環境変数）をサポート。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` 以下に純関数群を実装（DB 非依存、メモリ内計算）。
    - portfolio_builder: シグナル選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
    - risk_adjustment: セクターキャップ適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier)。
    - position_sizing: ポジションサイズ計算(calc_position_sizes)（risk_based / equal / score 対応）、単元株丸め、aggregate cap スケールダウンロジックなど。
    - 設計ドキュメント（PortfolioConstruction.md / StrategyModel.md）に基づく注釈・TODO を含む。

- 研究用ファクター計算
  - `kabusys.research.factor_research`：DuckDB を使ったファクター計算基盤を実装（モメンタム / MA200 / ATR 等の計算方針記述）。（partial 実装・続きあり）

- ロギング・ユーティリティ
  - `kabusys.utils.logging_setup`：ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度・CPU 固定ユーティリティ
  - `kabusys.utils.process_priority`：Windows / POSIX 差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを実装。
    - set_process_priority(level: "high" | "normal" | "low")：psutil を用いた優先度設定（権限不足時は警告してスキップ）。
    - set_cpu_affinity(cpu_count)：最初の N コアに固定（未対応 OS / 権限不足時は警告してスキップ）。

### 変更 (Changed)
- N/A（初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- N/A（初回リリースのため既知のバグ修正履歴はありません）

### 注意事項 / 既知の制約
- run_monitoring は監視データ用 SQLite として settings.sqlite_path（本番用）を使用する設計になっています。環境に応じた切り離しが必要な場合は設定を調整してください。
- config_setup による .env は機密情報を含むため絶対に Git にコミットしないでください（出力ヘッダに注意喚起を追加）。
- position_sizing や apply_sector_cap 内の一部ロジックには TODO コメントがあり、価格欠損時のフォールバックや銘柄別 lot_size の拡張など将来対応予定の項目があります。
- factor_research モジュールは設計方針と一部実装を含みますが、データスキャン範囲や完全実装（すべてのファクター計算）の確認が必要です。
- ログディレクトリ作成やプロセス優先度設定・CPU affinity の操作は環境（OS / 権限）に依存します。権限不足時は警告を出してフォールバックします。

### セキュリティ (Security)
- 環境変数に機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を扱うため、.env の取り扱いとアクセス制御に注意してください。validate_config によるチェックや config_setup の案内を利用してください。

---

（注）本 CHANGELOG はコードベースからの抽出・推測に基づいて作成しています。実際のリリースノートや運用上の判断は、コミット履歴やリリース管理方針に基づいて調整してください。
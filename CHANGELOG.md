# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 初回リリース
最初の公開リリース。システム全体のコアユーティリティ、実行・監視用エントリポイント、ポートフォリオ構成ロジック、設定管理ツールなどを含みます。

### 追加
- 全般
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたデータストレージを統合（設定でパス指定可能）。
  - ロギング統一ユーティリティ `kabusys.utils.logging_setup.setup_logging` を実装。コンソール出力（stdout）と日次ローテーションのファイル出力をサポート。
  - プロセス優先度 / CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を実装（Windows / POSIX の差分吸収、失敗時は警告でスキップ）。
  - 環境設定クラス `kabusys.config.Settings` を実装。環境変数から各種設定（DBパス、APIトークン、動作環境など）を取得するプロパティを提供。
  - 自動 .env 読み込み機能を追加（プロジェクトルート検出。.env / .env.local を OS 環境変数優先で読み込む。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env ファイルの堅牢なパース処理を実装（コメント、クォート、`export KEY=val` 形式に対応）。

- 実行・監視
  - 実行エンジン用エントリポイント `src/kabusys/run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - Broker クライアントを `BrokerClientFactory` から生成。依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立てて ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止制御: `data/stop_requested.flag` により実行停止を検知。`data/execution.pid` を PID ファイルとして使用。
  - 監視ループ用エントリポイント `src/kabusys/run_monitoring.py` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する（監視テーブル初期化を行う）。
    - 停止制御: `data/stop_requested.flag` によりループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連 CLI
  - 対話式 .env 作成ウィザード `src/kabusys/config_setup.py` を追加。
    - 主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を対話的に設定して .env を生成。
    - 既存 .env の読み込みと既存値再利用、シークレット項目のマスク表示、保存確認を実装。
  - 設定検証ツール `src/kabusys/validate_config.py` を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML インストール時は）パース検証を実行。
    - `--strict` フラグで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群、DB 非依存）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、タイブレークは signal_rank）を実装。
    - 等金額配分 `calc_equal_weights` を実装。
    - スコア加重配分 `calc_score_weights` を実装（全スコアが 0 の場合は等配分にフォールバックし警告）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限を適用する `apply_sector_cap` を実装（既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を実装（"bull"/"neutral"/"bear" をサポート、未知は 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出 `calc_position_sizes` を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）や cost_buffer を考慮したスケーリングロジックを実装。

- ツール
  - Paper Trading 検証レポート生成スクリプト `src/kabusys/tools/paper_verification_report.py` を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。
    - パス/フェイル閾値を定義（例: 稼働率 >= 99%、注文成立率 >= 90% 等）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）をサポート。
    - DB 内のテーブルが存在しない場合は安全に N/A を返す。

- リサーチ
  - ファクター計算モジュールの骨格 `src/kabusys/research/factor_research.py` を追加（モメンタム等の計算方針を実装予定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 注意事項 / 仕様
- run_monitoring は監視用 DB（Settings.sqlite_path）を環境に依らず使用する設計になっています（監視データは本番 DB に記録される想定）。
- run_execution は paper_trading 環境時に paper 用 SQLite を使用して本番 DB と完全分離します。
- .env の自動読み込みはプロジェクトルートが検出できない場合や、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定した場合はスキップされます。
- process priority / CPU affinity の設定は権限や OS により失敗することがあるため、失敗時はログ警告を出して処理を継続します。
- ログファイルディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続します。

### 既知の制限
- portfolio.position_sizing の lot_size はグローバル共通で固定（将来的に銘柄別対応を予定）。
- risk_adjustment.apply_sector_cap は price 欠損時にエクスポージャーが過少見積りされる可能性がある（TODO コメントあり）。
- factor_research はファイル末尾で未完の状態（実装継続予定）。

---

今後のリリースでは、Strategy/Execution 本体の詳細ロジック（StrategyModel、ExecutionEngine の細部）、バックテスト・シミュレーション機能、さらなるテストカバレッジの追加を予定しています。
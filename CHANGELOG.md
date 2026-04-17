# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
慣例: Unreleased → 次回リリースに向けた変更 / 各バージョンごとに Added / Changed / Fixed / Security 等で整理します。

## [Unreleased]
- （現在のスナップショットからの変更は未リリースです）

## [0.1.0] - 2026-04-17
最初の公開リリース — KabuSys の基礎機能を実装しました。  
主に環境設定、監視/実行のランナー、ポートフォリオ構築、ポジション計算、リスク調整、リサーチ・ファクター計算、ユーティリティ群、ツール群を含みます。

### Added
- 基本パッケージ情報
  - バージョン定義: `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定・管理
  - Settings クラス (`kabusys.config`) を実装。環境変数から各種設定（DBパス、APIトークン、実行環境など）を取得。
  - .env 自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み、OS環境変数を保護。
  - .env ファイルの厳密なパース実装（コメント、export 形式、クォートやエスケープ対応）。
  - `kabusys.config_setup` による対話式ウィザードを追加。`.env` の初期作成・更新を支援。
  - `kabusys.validate_config` による設定検証 CLI を追加。必須環境変数、パス、YAML ファイルの存在・パース、ライブ環境時の追加警告などをチェック。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、本番 DB から完全分離された `data/paper_trading.db` を使用。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイルの取り扱いによる安全停止をサポート。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔オーバーライド（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視データの一貫性を確保）。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力と次回ポーリングまでの待機。

- モニタリング DB 初期化
  - `kabusys.monitoring.monitoring_db` 経由で監視テーブルの初期化（起動時の冪等性を確保）。

- 実取引・ペーパートレード分離
  - Settings に `paper_sqlite_path`、`is_paper` 判定を実装。Paper Trading 環境では専用 SQLite を使用して本番 DB とデータ分離。

- ポートフォリオ構築（pure functions）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合のフォールバック処理を含む。
  - `kabusys.portfolio.position_sizing`
    - position size（発注株数）計算を実装。`risk_based` / `equal` / `score` の allocation_method をサポート。
    - lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング処理を実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集約上限適用（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research`
    - DuckDB 接続を受け取り、Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR）、Liquidity（出来高・売買代金）等のファクターを計算する関数群を実装。
    - DuckDB の SQL/ウィンドウ関数を活用した実装で大量データの集計に対応。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - プロセス優先度（high/normal/low）設定をクロスプラットフォームに対応して実装（Windows と POSIX を吸収）。
    - CPU affinity 固定機能（set_cpu_affinity）を追加。
    - エラー時には警告ログで安全にフォールバック。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力する CLI ツールを実装。
    - デフォルトの合格基準（稼働率 99%、填充率 90%、送信率 95%、P95 レイテンシ 200ms）を用いて PASS / FAIL 判定を行う。
    - 日付レンジ指定（--from / --to）や DB パス指定（--db）をサポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env 読み込みの堅牢性向上
  - export プレフィックス、クォート内のエスケープシーケンス、インラインコメントの扱いなどを正しくパースすることで、.env の読み込みによる誤設定を低減。

### Documentation / Usage notes
- CLI:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 環境変数の主なデフォルト値:
  - SQLITE_PATH: data/monitoring.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - MONITOR_POLL_INTERVAL: 60 (秒)
  - PID_FILE_PATH: data/execution.pid

- セキュリティ注意:
  - .env ファイルは絶対にリポジトリへコミットしないでください（config_setup でもヘッダで注意喚起を追加）。

### Internal / Implementation notes
- DuckDB と SQLite を併用
  - 分析用には DuckDB（高速な列指向処理）、監視/履歴保存には SQLite を採用。
- Paper Trading モードでは本番 DB から完全に分離してデータを記録することで、テストと本番の混同を防止。
- ポートフォリオ・ポジション計算は純粋関数として実装されており、ユニットテストが容易な設計。

---

今後の改善案（例）
- 各関数・クラスに対するユニットテストの整備
- position_sizing に銘柄別 lot_size サポートを追加（現状は全銘柄共通で lot_size を使用）
- 価格欠損時のフォールバック（前日終値や取得原価）を導入して誤ったエクスポージャー判定を防止
- Paper Trading レポートの出力を CSV/JSON にエクスポートする機能

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリース計画に合わせて適宜修正してください。）
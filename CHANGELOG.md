# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。

全般:
- リポジトリの初期機能群を実装・公開（バージョン 0.1.0）
- バージョンはパッケージメタデータで __version__ = "0.1.0"

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本設定管理
  - Settings クラスを実装。環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、実行環境など）を取得する機能を提供。
  - プロジェクトルート（.git または pyproject.toml）から .env/.env.local を自動読み込みする仕組みを導入。OS 環境変数保護（protected keys）による上書き制御をサポート。
  - 必須環境変数チェック用の内部関数 `_require` を実装（未設定時は ValueError）。

- 起動スクリプト / 実行運用
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。設定に応じて paper_trading 用の専用 SQLite DB を使用（PAPER_TRADING_SQLITE_PATH / Settings.is_paper）。BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動・停止制御を実装。実行中の停止は data/stop_requested.flag と execution.pid を利用。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用。起動時にプロセス優先度を High に設定。

- 設定支援ツール / 検証
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。秘密情報はマスク表示、既存値の再利用、.env ファイルへの書き出し機能を備える。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、DB パス検査、config/*.yaml ファイルの存在・パース検証（PyYAML がない場合は警告）を実行。--strict オプションで警告を失敗扱いにできる。

- モニタリング / 実行の補助
  - monitoring_db 初期化を呼び出す処理を run_execution/run_monitoring に組み込み（冪等）。
  - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。

- ユーティリティ
  - process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し psutil を利用。権限不足や未対応 OS 時は警告を出してスキップ。
  - set_cpu_affinity 関数により指定コア数へのピン留めをサポート（未指定時は全コア使用）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア順ソートと上位選定。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（スコア合計が 0 の場合は等配分へフォールバック、警告ログ）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を基にセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外）。unknown セクターは上限適用対象外。sell_codes による当日売却予定銘柄の除外に対応。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告ログの上で 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。lot_size 単位で丸め、1 銘柄上限（max_position_pct）・合計利用上限（max_utilization）を考慮。cost_buffer による手数料・スリッページ考慮、投資合計が available_cash を超える場合はスケーリング（残差配分ロジック含む）を実装。価格欠損や 0 の場合はスキップ。

- Research / ファクター計算
  - research.factor_research:
    - calc_momentum: DuckDB の prices_daily テーブルを用いて 1M/3M/6M リターンと 200 日移動平均乖離率（ma200_dev）を計算する関数を実装。データ不足時の None ハンドリングあり。
    - calc_volatility: ATR（20 日）、相対 ATR、20 日平均売買代金、出来高比率などを計算する関数を実装（true_range の NULL 伝播制御など、欠損制御に配慮）。
  - 設計方針として DuckDB 接続を受け取り SQL と Python で計算し、外部 API へはアクセスしない点を明記。

- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し、閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms）に対する PASS/FAIL レポートを出力する CLI を追加。
    - P95 計算ユーティリティ、日付フィルタ(--from/--to/--db オプション) をサポート。DB ファイルが存在しない場合のエラーメッセージを実装。

- パッケージ初期化
  - kabusys.__init__: パッケージメタ情報と __all__ の設定を追加。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意事項 / 移行ガイド
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きを追加）。
- 本番運用時は KABUSYS_ENV を "live" に設定し、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などを確認してください。validate_config.py の --strict モードで起動前チェックを推奨します。
- Paper trading と本番 DB は分離されています。paper_trading 実行時は Settings.is_paper により paper_sqlite_path が使用されます。
- プロセス優先度・CPU affinity 設定は権限・プラットフォーム依存です。権限不足時は警告が出力されますが処理は継続されます。
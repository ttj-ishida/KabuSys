# CHANGELOG

すべての変更は Keep a Changelog の構成に準拠しています。  
このファイルはソースコードの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

- （現在差分なし）

## [0.1.0] - 2026-04-17

追加（Added）
- 初期リリースを追加。
- アプリケーションメタデータ:
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 実行用エントリスクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト `data/paper_trading.db`）を使用し MockBrokerClient を利用する仕組みをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能、デフォルト 60 秒）。監視処理は環境に関わらず本番の sqlite パスを使用する設計。
- 環境設定・検証用 CLI を追加:
  - config_setup.py: 対話式ウィザードで `.env` を作成/更新するツール。生成される `.env` に関する注意書きを同梱（誤って Git にコミットしないよう明示）。
  - validate_config.py: `.env` と `config/*.yaml` の整合性を起動前に検証する CLI（`--strict` オプションで警告を失敗扱いにできる）。
- 設定管理モジュールを追加:
  - config.py: 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（OS 環境変数保護、`.env.local` は `.env` を上書き）、`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。Settings クラスに多数のプロパティ（DB パス、API トークン、監視閾値、環境判定等）を提供。`PAPER_FILL_MODE` の妥当性チェックや `KABUSYS_ENV` の有効値チェックを実装。
- 監視 DB 初期化ユーティリティの利用:
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等）。
- Execution モジュールの組立て:
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組立てと起動ロジック。
  - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80 など）を採用し、初期ポートフォリオ値に broker.get_available_cash() を使用。
- Paper Trading 検証レポート:
  - tools/paper_verification_report.py: Paper Trading の SQLite（デフォルト `data/paper_trading.db`）から集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを算出して PASS/FAIL を判定する CLI。
  - デフォルト判定基準（例: 稼働率 >= 99%、注文成功率 >= 90%、P95 <= 200ms）を定義。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補銘柄選択（スコア降順、signal_rank によるタイブレーク）、等金額・スコア加重の重み計算（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）実装。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能資金に基づくスケーリング）、手数料/スリッページのための cost_buffer を考慮した調整ロジックを搭載。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存保有をセクター別に集計して上限超過セクターの候補を除外）とレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear を想定、未知のレジームは警告出力後 1.0 でフォールバック）。
- リサーチ / ファクター計算:
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily 等のテーブルからモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR 20 等）、流動性指標を計算する関数（calc_momentum, calc_volatility 等）を実装。計算範囲のバッファや欠損データの扱いについてドキュメントを添付。
- ユーティリティ:
  - utils/process_priority.py: Windows / POSIX 差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。権限エラーや未対応プラットフォームは警告を出して無視する設計。
- パッケージ構成:
  - kabusys/__init__.py にて主要モジュールをエクスポート（portfolio 等）。

変更（Changed）
- 環境変数ロードの優先度ルール:
  - OS 環境変数 > .env.local > .env の順で読み込み。`.env.local` は `.env` を上書きする振る舞いを採用。
- .env パーサーの挙動強化:
  - クォートあり値のバックスラッシュエスケープ処理、クォートなし値のインラインコメント処理（コメントは直前がスペース/タブ の場合のみ）に対応。`export KEY=val` 形式にも対応。
- Execution / Monitoring の DB パス取扱い:
  - Monitoring は環境に関係なく Settings.sqlite_path（本番用監視 DB）を参照するように設計。Execution は `is_paper` の場合に paper_sqlite_path を使用して paper_trading DB と本番 DB を分離。
- run_monitoring のポーリング設定:
  - 環境変数 `MONITOR_POLL_INTERVAL` を導入してポーリング間隔を上書き可能（0 以下や不正な値はデフォルト 60 秒にフォールバックし警告を出力）。
- Paper Trading 検証レポート:
  - P95 の計算は小さなサンプルに対しても妥当なインデックスを選ぶ実装（ceil を利用）。存在しないテーブルやカラムに対しては sqlite3.OperationalError を捕捉して欠損値（N/A）扱いにフォールバック。
- ロギング / メッセージ改善:
  - 各モジュールで debug/info/warning を適切に出力するよう整備（例: calc_score_weights が全スコア 0 のときの警告、apply_sector_cap の除外デバッグメッセージ等）。

修正（Fixed）
- process_priority のエラー耐性:
  - アクセス権限不足や未実装 API で発生する例外（psutil.AccessDenied, AttributeError, NotImplementedError）を捕捉して警告を出し、正常終了を継続するように変更。
- run_execution/run_monitoring のシャットダウン動作:
  - プロセス終了時に SQLite / DuckDB 接続を確実にクローズする finally ブロックを追加。
  - 停止フラグ（data/stop_requested.flag）を検出して安全にループを抜けるロジックを実装。

セキュリティ（Security）
- config_setup にて生成される .env への注意書きを同梱（絶対に Git へコミットしない旨）。validate_config による本番（live）時の LINE 通知未設定チェックや KILL_FLAG_CLEAR_ON_START の危険性警告を実装。

破壊的変更（Breaking Changes）
- なし（初期リリース）。

注記（Notes）
- 内部的に DuckDB / SQLite / psutil / yaml（PyYAML）等の外部依存を参照する機能があり、環境によっては追加インストールが必要。
- `.env` 自動読み込みはデフォルトで有効。テストや特殊環境で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading と本番データは明確に分離されるよう設計されていますが、運用上の注意（ファイルパス確認、Kill Switch 設定等）は validate_config で必ず確認してください。

---

今後の提案（今後の改善案・ TODO）
- position_sizing: 銘柄別の lot_size を扱うために、将来的に stocks マスタから lot_size を読み込む設計へ拡張する旨の注記あり（TODO）。
- apply_sector_cap: price 欠損時に過少見積りされる問題へのフォールバック（前日終値や取得原価の利用）を将来対応候補として記載。
- factor_research: 追加ファクターや Z スコア正規化ユーティリティ連携の拡充。

（以上）
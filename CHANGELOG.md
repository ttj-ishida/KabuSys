# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

全般
- 初期リリース。内部設計に基づく CLI / ライブラリ群を追加。

[0.1.0] - 2026-04-17
--------------------

Added
- アプリケーション設定管理を追加（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスで主要環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）やパス、動作モード（development / paper_trading / live）を提供。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID / kill flag 関連など多数の設定項目をプロパティとして提供し、入力検証を実施。

- 環境設定ウィザード CLI を追加（kabusys.config_setup）。
  - 対話式で .env を作成・更新するツール。
  - デフォルト値、選択肢、秘密値マスクなどをサポート。
  - .env の書式固定化（コメント付きヘッダ）と保存機能を備える。

- 設定検証 CLI を追加（kabusys.validate_config）。
  - .env と config/*.yaml の存在・簡易パース（PyYAML 利用時）・パラメータ整合性を検証。
  - --strict オプションで警告を失敗扱いにできる。
  - 本番環境（KABUSYS_ENV=live）向けのガード（LINE 設定や Kill Switch 周りの注意）を実装。

- 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
  - ExecutionEngine を起動するためのエントリポイント。
  - KABUSYS_ENV=paper_trading 時は専用の paper trading SQLite DB を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカ抽象化、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動を実装。
  - 停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連等）を提供。

- 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
  - SystemMonitor を使ったポーリング監視ループを提供。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず本番 monitoring DB を使用する仕様）。
  - 停止フラグ検知、例外時のログ出力、リソースクローズ処理を実装。

- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX（Linux/Mac/FreeBSD）間の差分吸収。
  - set_process_priority("high"|"normal"|"low") と set_cpu_affinity() を提供。
  - 権限不足や未対応プラットフォームでは警告ログを出して安全にスキップ。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクターキャップ適用（apply_sector_cap）、レジームに応じた資金乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数算出（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め、aggregate cap（利用可能現金に応じたスケールダウン）、手数料・スリッページのバッファ考慮等を実装。

- 研究用ファクター計算モジュールを追加（kabusys.research.factor_research）。
  - Momentum、Volatility（ATR 等）、Liquidity、Value 等の計算ロジック（DuckDB 経由で prices_daily, raw_financials を参照）。
  - P95 等の統計補助、および窓幅やスキャン日数の定数を実装。
  - DuckDB を使ったウィンドウ集計 SQL を組み合わせた設計。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）。
  - ペーパートレード用 SQLite DB を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を行う。
  - デフォルト閾値を定義（稼働率>=99%、成立率>=90%、送信率>=95%、P95<=200ms）。
  - --from/--to/--db オプションをサポート。

- パッケージメタ情報（kabusys.__init__）にバージョン (0.1.0) を追加。

Changed
- （初期リリース）なし

Fixed
- （初期リリース）なし

Deprecated
- （初期リリース）なし

Removed
- （初期リリース）なし

Security
- （初期リリース）なし

注意事項 / マイグレーション
- .env の自動読み込み挙動
  - OS 環境変数 > .env.local > .env の優先順位でロードされます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）が使用され、本番 monitoring DB（SQLITE_PATH）とは分離されます。
- モニタリングループは常に sqlite_path（本番 monitoring DB）を参照します。
- MONITOR_POLL_INTERVAL：ポーリング間隔を秒で指定（整数、1 以上）。不正な値はデフォルト 60 秒にフォールバックして警告を出します。
- PID / stop flag / kill flag
  - 停止フラグは data/stop_requested.flag（プロジェクトルート下）を使用してプロセスの安全停止を実現します。
  - 実行エンジンは data/execution.pid を PID ファイルとして扱います。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に Kill Flag を自動クリアしますが、推奨は 0（無効）です。validate_config にて注意喚起があります。
- 権限・互換性
  - set_process_priority / set_cpu_affinity は OS や権限に依存します。サポート外プラットフォームや権限不足時は警告ログを出してスキップされます。

使い方（抜粋）
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

開発者向けメモ（コードからの推測）
- 多くのモジュールは純粋関数設計（DB 参照の有無を明確化）で、テスト容易性を考慮。
- DuckDB を解析用途に採用しており、prices_daily / raw_financials を参照した SQL ベースのファクター計算を中心に設計。
- Execution 側は Broker 抽象化と RiskManager による安全弁を組み合わせ、paper_trading 時は MockBroker を用いる想定。

お問い合わせ・報告
- この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートや運用上の仕様はソース管理の正式なリリース記録に従ってください。問題や誤りを見つけた場合は差分を提供してください。
CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-19
-----------------

Added
- 初期リリースを追加（__version__ = 0.1.0）。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBroker を想定）。
    - OrderRepository、OrderManager、RiskManager（デフォルト設定あり）、Reconciler を組み立てて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）検知で安全に停止。実行中は PID を data/execution.pid に記録。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視 DB に記録。
    - 停止フラグファイル検知でループを終了。例外発生時はログを残して次のポーリングを継続。

- 設定関連
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの .env, .env.local を読み込み。OS 環境変数を保護）。
    - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応）。
    - Settings クラスを提供し、各種環境変数（J-Quants, kabu API, DB パス, Paper Trading 設定, 監視閾値など）をプロパティとして安全に取得。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。

  - config_setup.py: 対話式 .env 生成ウィザードを追加（.env の初期作成・更新。機密項目はマスク表示、保存前に確認プロンプト）。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時のガードチェックを実装。
    - --strict オプションで警告も失敗扱いに。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークに signal_rank）。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を参照し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分ロジック実装。
    - lot_size 単位で丸め、1銘柄上限や aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りと端数処理を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテート（TimedRotatingFileHandler、30日保管）をルートロガーに設定。LOG_DIR / LOG_LEVEL から設定可能。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows/Linux/macOS の差を吸収して優先度と CPU affinity を設定。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び、監視用テーブルが存在することを保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 DB を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下件数、API レイテンシ（avg / max / P95）。
    - 閾値を定義して PASS/FAIL を判定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency <= 200 ms など）。
    - --from / --to / --db オプションで期間・DB 指定可能。

- リサーチ（骨組み）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum 関数や定数群を実装開始（prices_daily / raw_financials テーブルを参照する設計）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- .env の生成テンプレート（config_setup）内で「.env を絶対に Git にコミットしない」旨の注意喚起を追加。

Notes / Known issues / TODO
- portfolio/position_sizing.calc_position_sizes:
  - 将来的に銘柄毎の lot_size をサポートする旨の TODO コメントあり（現在は全銘柄共通 lot_size）。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来のフォールバック価格戦略が記載されている（TODO）。
- research/factor_research.py は現時点で実装が途中（ファイル末尾で途中切れの痕跡あり）。実運用前に関数の完成とテストが必要。
- run_monitoring.py は監視用 DB 接続に sqlite3 を使用し、duckdb も開く設計。運用時の接続・ロック挙動は環境に依存するため運用確認推奨。

その他
- 起動スクリプト（monitoring / execution）はプロセス優先度設定やログ設定を最初に行い、運用時の観測性と安定稼働を重視する設計になっています。
- validate_config の YAML 検証は PyYAML 未導入時にスキップし、依存性がない場合でも致命的にならないよう配慮されています。

----------

上記はコードベースの現状から推測して作成した変更履歴です。必要であれば、リリース日や各項目の詳細（関連ファイルや関数名）を調整して正式ドキュメント化します。
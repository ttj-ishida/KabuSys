CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし（現時点ではリリース済みの内容を以下にまとめています）。

0.1.0 - 2026-04-21
------------------

Added
- 基本アーキテクチャとコア機能を実装（初期リリース）。
  - パッケージ識別子: kabusys v0.1.0
- 実行・監視用の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine をスレッドで起動し、data/execution.pid に PID を書く仕組み。
    - 停止フラグ (data/stop_requested.flag) を検出して安全に停止する機構。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する仕組み（MockBrokerClient の使用を想定）。
    - ブローカー生成は BrokerClientFactory 経由。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構築。
    - デフォルトのリスク設定を RiskConfig として組み込み（例: max_position_pct=0.20, max_utilization=0.80 等）。
  - run_monitoring.py
    - SystemMonitor をポーリングで実行する起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視 DB は環境に関わらず本番の sqlite_path を使用する挙動。
    - 停止フラグ検出でループを終了、KeyboardInterrupt にも対応。
- 環境設定・管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env/.env.local を読み込み、OS 環境変数を保護する仕組み（protected set）。
    - 複数の設定プロパティを提供（J-Quants、kabuAPI、DBパス、Paper Trading 用設定、監視閾値、KABUSYS_ENV の検証など）。
    - PAPER_FILL_MODE の検証や PAPER_TRADING_SQLITE_PATH、PID/kill flag のパス設定等を含む。
  - config_setup.py
    - 対話式 .env ウィザードを実装。既存 .env を読み込み、項目ごとに対話入力、保存処理を提供。
    - 出力テンプレートに注意書き（.env を絶対に Git にコミットしない等）。
  - validate_config.py
    - 起動前検証 CLI を実装（必須環境変数の検査、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在・パース確認、live 環境向けの追加警告等）。
    - --strict オプションで警告を FAIL と扱うモードを提供。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する堅牢性。
  - utils/process_priority.py
    - プラットフォームを抽象化したプロセス優先度設定（high/normal/low）と CPU affinity 設定機能。
    - Windows と POSIX（Linux/Mac/FreeBSD）を考慮した実装、権限不足時に警告を出してスキップする動作。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank でタイブレーク）、等金額配分、スコア加重配分を実装。スコア全0の際は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジション・価格マップを用いてセクターエクスポージャーを算出し閾値を超えるセクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく乗数、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method="risk_based" / "equal" / "score" に対応した株数計算ロジックを実装。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮。
    - cost_buffer を用いた保守的なコスト試算と、合計コスト超過時のスケーリング（残差処理で lot 単位で再配分）を実装。
    - 不足データ（価格がない等）をスキップし、ログを出力する堅牢性。
- 解析・調査用モジュール
  - research/factor_research.py（ファクター計算基盤）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針を実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - モメンタム計算関数（calc_momentum）の骨格・定数を定義（実装は部分的）。
- ユーティリティ・ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から検証レポートを生成する CLI を実装。
    - 稼働率、注文成立率、送信率、P95 レイテンシ等の指標を集計し、閾値（例: uptime >= 99%、fill rate >= 90%、P95 <= 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）や DB パス指定（--db / 環境変数）に対応。
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後の動作安定化を意図）。
- MONITOR_POLL_INTERVAL の不正な指定（0 以下や非数）はデフォルト（60秒）へフォールバックし警告を出す。
- run_monitoring は監視 DB に本番 sqlite_path を使用するため、監視だけで別 DB を使いたい場合は設定を見直す必要がある。
- run_execution は paper_trading の場合データベースを明確に分離することで実トレードとデータ混在を避ける設計。
- process_priority / set_cpu_affinity は権限・プラットフォーム依存で失敗する可能性があるため、失敗時は警告を出して継続する安全策を実装。
- position_sizing の aggregate スケーリングでは lot_size 単位で切り捨て／残差再配分を行うため、厳密な投資合計が available_cash に到達しない場合がある（設計上の仕様）。
- research/factor_research.py はファクター計算の設計方針を含むが、いくつかの関数は部分実装のまま（今後の実装継続が必要）。

今後の予定（例）
- factor_research の完全実装（DuckDB SQL/集計ロジックの完成）。
- ExecutionEngine / SystemMonitor の単体テスト充実、MockBroker の実装詳細の確定。
- 銘柄ごとの lot_size をマスタ化し position_sizing を拡張。
- モニタリング指標の通知（LINE 連携）やアラート閾値のダイナミック化。

（各項目はコードの内容から推測して作成しています。実際の設計意図や将来計画はリポジトリのドキュメント/設計資料を参照してください。）
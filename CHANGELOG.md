# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。重要な実装内容はコードから推測して記載しています。

最新の変更
------------

Unreleased
: 現時点では未リリースの作業はありません。

リリース履歴
------------

### [0.1.0] - 2026-04-21

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を実装しています。主な変更点・追加点は以下の通りです。

Added
- 全体
  - パッケージ基本構成を追加。バージョンを `__version__ = "0.1.0"` として設定。
  - モジュールのエクスポートを定義（portfolio 等の主要 API を公開）。

- 実行/運用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - 実行前にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッション実行をスレッドで開始。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応し、安全に停止・終了する制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は環境に関係なく本番の `sqlite_path` を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB 接続、SystemMonitor の単発チェックループを実行。停止フラグ検知・KeyboardInterrupt に対応してクリーンに終了。

- 設定管理 / CLI
  - config.py: 環境変数と .env ファイルの読み込み・設定取得用の Settings を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動ロードを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - .env のパースは quotes、エスケープ、行内コメント等に対応した堅牢な実装。
    - 各種設定プロパティを提供（DB パス、LINE トークン、閾値、KABUSYS_ENV 検証、PAPER_FILL_MODE の検証など）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。
    - 対話で必須・オプション項目を入力し `.env` を生成。既存値の読み込みやシークレットのマスク表示に対応。
  - validate_config.py: 起動前に設定不備を検出する検証ツールを実装。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未導入時は警告）を実行。
    - `--strict` オプションで警告を失敗扱いにできる。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs を集計し、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均・最大・P95）などを計算して表示。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - 合格基準（しきい値）を定義（例: uptime >= 99%、fill_rate >= 90% 等）し、PASS/FAIL 判定を出力。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナルの選定（スコア降順・タイブレーク）、等金額／スコア加重の重み計算を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションをベースにセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - weights と候補に基づく発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）、最大ポジション比率、最大利用率、コストバッファを考慮した aggregate cap の適用、スケールダウンと端数処理（lot 単位での補正・残差配分）を実装。
    - price 欠損の扱いや将来的な拡張（銘柄別 lot_size）について TODO コメントあり。

- 研究用
  - research/factor_research.py（ファクター計算の骨格を追加）
    - Momentum、Value、Volatility、Liquidity といったファクター設計に基づく計算関数群を想定。DuckDB 接続で prices_daily / raw_financials を参照して計算する方針を明記。
    - モメンタム計算（calc_momentum）の実装開始（ファイル末尾で途中実装の痕跡あり）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時やファイルハンドラ作成失敗時はフォールバックしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py
    - プラットフォーム抽象化されたプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）と CPU affinity 設定を実装（psutil を使用）。権限不足や未対応 OS では警告を出してスキップ。

Changed
- 監視（monitoring）挙動
  - run_monitoring は環境（KABUSYS_ENV）に関わらず監視用 DB 接続に本番の sqlite_path を使用する実装とした（設計上、監視データは本番 DB に記録する意図）。
- .env 自動読み込みポリシー
  - OS 環境変数を上書きしない保護機構（protected set）を導入。.env.local は .env を上書きする仕様。

Fixed
- なし（初回リリースのため既知の問題点を警告・TODO としてコード内に残しています）。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数のシークレット値（J-Quants, kabu API password, LINE token）は対話ウィザードでマスクし、.env ファイルに平文保存する旨を注意喚起（.env を絶対に Git にコミットしないことをドキュメントヘッダに明記）。

Notes / Known issues & TODO
- position_sizing.calc_position_sizes:
  - 銘柄ごとの lot_size を将来的にサポートするための拡張 TODO を残しています。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積もられる問題があり、将来的にフォールバック価格（前日終値など）を利用する検討が必要。
- research/factor_research.py:
  - ファイル末尾が途中で切れている/未完部分があり、ファクター計算の完全実装が未完です。
- run_monitoring.py / run_execution.py:
  - 停止制御はファイルフラグ（data/stop_requested.flag）ベース。環境によりファイルパスを調整可能。

開発者向け補足
- Python 環境依存:
  - 一部機能（プロセス優先度設定、CPU affinity、psutil に依存）や YAML 検証（PyYAML）が外部パッケージに依存します。実行環境にこれらがない場合は該当チェック／機能は警告を出してスキップされます。
- ロギング:
  - StreamHandler は stdout に向けて設定されています。cron 等から起動する場合に stdout/stderr 両方を一本化してリダイレクトする運用を想定しています。

今後の予定（提案）
- research モジュールのファクター計算を完成させる（Momentum 等）。
- テストカバレッジの追加（特に portfolio の数値処理・端数処理のロジック）。
- 銘柄別 lot_size の導入と price フォールバックロジックの実装。
- ExecutionEngine / BrokerClient のモックを用いた統合テストの整備。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先して更新してください。
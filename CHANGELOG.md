CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------
（なし）

0.1.0 - 2026-04-19
-----------------
最初の公開リリース。コードベースから推測できる主要機能・改善点をまとめます。

Added
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 設定・環境変数関連
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - 高度な .env パーサを実装：コメント・export プレフィックス・シングル/ダブルクオート内のエスケープをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを実装し、環境変数値の取得・検証を統一（各種デフォルト値、列挙値チェック、Paper Trading 用 DB パス、閾値設定などを提供）。
  - .env の対話式ウィザード（kabusys.config_setup）を追加。対話的に .env を生成/更新可能（--env-file オプション対応）。

- 設定検証
  - kabusys.validate_config CLI を追加。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が利用可能な場合）を検証。
  - --strict フラグで警告も失敗（exit 1）として扱うモードを提供。

- 起動スクリプト / デーモン管理
  - run_execution.py: ExecutionEngine 起動用エントリ。以下の機能を含む:
    - プロセス優先度を high に設定する仕組みを呼び出し。
    - 環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / Settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成（KABUSYS_ENV=paper_trading 時は MockBroker を使用する想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine を起動。PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - RiskManager のデフォルト設定（max_position_pct など）と、initial_portfolio_value を broker.get_available_cash() から初期化。

  - run_monitoring.py: SystemMonitor のポーリング起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値は警告のうえデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番データを参照する設計）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了。
    - check_once() 実行時の例外はログに記録して次のポーリングに継続する堅牢化。

- ロギング・プロセス管理ユーティリティ
  - logging_setup: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority: Windows/Linux（および一部 POSIX）向けにプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足時は警告を出してスキップする安全設計。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 配分比率計算（スコア全0 は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用。既存保有のセクター別時価を算出し上限超過セクターの候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear とフォールバック）。
  - position_sizing:
    - calc_position_sizes: 重み・候補・ポートフォリオ状況から発注株数を計算。risk_based / equal / score の allocation_method をサポート。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を上回る場合のスケーリング）を実装。cost_buffer を用いた保守的なコスト見積りと小数端数の配分アルゴリズムを実装。

- Paper Trading サポートと検証ツール
  - ExecutionEngine 等は paper_trading モードをサポートし、paper 用 DB（data/paper_trading.db）へ記録することで本番 DB と分離。
  - tools.paper_verification_report: Paper Trading データベースから稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL レポートを生成するスクリプトを追加。閾値（稼働率 99% など）と日付フィルタ（--from / --to）、--db オプションを提供。

- データ解析（研究）モジュール（途中実装）
  - research.factor_research: モメンタム等のファクター計算機能の実装を追加（DuckDB 経由で prices_daily/raw_financials を参照する設計）。モメンタム周期などの定数が定義され、calc_momentum 関数の一部が実装済み（ファイル末尾で途中）。

Changed / Improved
- 環境変数ロード順序を明確化: OS 環境 > .env.local > .env（.env.local は .env の設定を上書き）。
- .env 読み込み時に OS 環境変数を保護（protected set）し、意図しない上書きを防止。
- logging_setup: ファイルハンドラ作成失敗やディレクトリ作成失敗時にフォールバックして動作継続する堅牢化。コンソールは stdout を使用（stderr ではない）。
- process_priority: プラットフォーム差異を吸収する実装（Windows 定数を getattr で安全に参照、POSIX で nice 値を設定）。権限不足時にはログ警告で継続。
- run_monitoring のポーリングループは check_once() 内での例外をハンドリングしてループ継続するように改善（単一の例外で監視が停止しない設計）。
- calc_score_weights / calc_regime_multiplier 等でのフォールバックロジック（スコア全0 や未知レジーム時に安全なデフォルトを採用）を明示化。

Fixed
- .env 内の引用符つき値・エスケープ・行内コメントを正しく処理することで、複雑なシークレット値や URL を誤読しないよう修正。
- ポジションサイズ計算における aggregate cap 適用時の端数処理を改善（lot_size 単位で安定した再配分ロジックを導入）。

Notes
- 監視 DB（monitoring）に関する初期化は init_monitoring_db(sqlite_conn) で行われ、冪等にチェック・作成される想定。
- run_execution/run_monitoring は stop flag ファイル（data/stop_requested.flag）や PID ファイル（data/execution.pid / data/execution.pid に相当）を使って外部からの停止/管理を行う設計。
- validate_config は PyYAML がない環境でも動作し、YAML の内容検証はスキップして警告する。
- research.factor_research はまだ途中実装（calc_momentum の実装開始）で、完全なファクター群の計算は今後の拡張が必要。

未解決 / 今後の改善候補
- position_sizing の price フォールバックロジック（price が欠損時の扱い）について注記があり、前日終値などを使ったフォールバックを検討する余地がある。
- research.factor_research の続き（ファクター計算の完成）および単体テストの追加。
- logging_setup の細かなローテーション設定やクラウド・コンテナ環境での標準出力運用ポリシー整備。
- 単体テスト・統合テストの充実（特に ExecutionEngine / Broker クライアント周りのモックテスト）。

ライセンス / セキュリティ
- 本 CHANGELOG はコードベースから推測して作成しています。実運用時には機密情報の扱い（.env の管理、ログにシークレットが出力されないことなど）に注意してください。
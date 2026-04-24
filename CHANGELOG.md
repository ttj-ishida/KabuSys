# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ (日本語訳に準拠)

## [Unreleased]

### Added
- —（現在の差分はありません。次のリリースに向けて変更を記載してください）—

---

## [0.1.0] - 2026-04-24

初回リリース。プロジェクトの主要機能とユーティリティを導入しました。

### Added
- 実行エントリ／デーモン起動スクリプト
  - run_execution.py
    - ExecutionEngine をスレッドで起動して管理（停止フラグ検出によるグレースフルシャットダウン対応）。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - 実行 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）検出でループを終了。
    - 監視は環境に依らず本番 sqlite_path を使用して監視データを記録。

- 設定・環境管理
  - config.py
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - 高度な .env パーサ実装:
      - export プレフィックス対応、クォート文字（' "）内のエスケープ対応、インラインコメントの扱い（クォート有無で異なる扱い）。
      - _load_env_file による protected（OS 環境変数）を保持するオプション。
    - Settings クラスによりアプリ設定をプロパティとして提供（検証付き: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）。
    - Paper Trading 用 sqlite パス（PAPER_TRADING_SQLITE_PATH）や PID/KILL フラグパスなど多数の設定項目を標準化。

  - config_setup.py
    - 対話式 .env ウィザード。既存 .env 読み込み・編集、選択肢・シークレット入力・保存確認をサポート。
    - 生成される .env のテンプレート（コメント付き）を提供。

  - validate_config.py
    - 起動前チェック CLI。必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無い場合は検証スキップ）等を実施。
    - --strict モードで警告も失敗扱いにできる。

- 監視・検証ツール
  - monitoring 初期化: init_monitoring_db 呼び出しで監視テーブルの有無を冪等に保証。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを生成する CLI。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、レイテンシ（avg/max/P95）、リスク却下数など。
    - しきい値に基づく PASS/FAIL 判定を実装（稼働率 >= 99% 等、スクリプト内定義）。
    - 日付フィルタ、DB パスの引数/環境変数による指定対応。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 重み計算: 等分配(calc_equal_weights)、スコア加重(calc_score_weights)。全スコアが 0 の場合は等分配へフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）。既存ポジションのセクターエクスポージャを計算し、上限超過セクターの新規候補を除外。
    - レジーム乗数(calc_regime_multiplier): "bull"/"neutral"/"bear" に対する投資乗数を返却。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 株数決定アルゴリズム（calc_position_sizes）:
      - allocation_method: "risk_based"/"equal"/"score" をサポート。
      - 単元株（lot_size）単位で丸め、ポジション上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
      - aggregate cap 超過時はスケールダウンし、残余キャッシュで小数部の大きい順に lot 単位の追加配分を行う。
      - cost_buffer（手数料・スリッページ見積り）考慮。
    - 不足データ（価格欠損等）に対するログ出力とスキップ処理を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーにセット。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を明示。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定(set_process_priority)と CPU affinity 設定(set_cpu_affinity)を提供。
    - Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収。権限不足や未対応 OS の場合は警告してスキップ。

- データ処理（部分的実装）
  - research/factor_research.py（ファクター計算の基盤を実装）
    - モメンタム系ファクター計算の定義（1M/3M/6M リターン、MA200 乖離など）と計算用定数を導入。DuckDB 接続を前提として prices_daily / raw_financials を参照する設計方針を採用。
    - P95 等の統計ユーティリティや日付フィルタロジックを含む。

### Changed
- ロギングを stdout（StreamHandler）へ出力する設計を採用（cron/Task Scheduler での取り扱いを考慮）。
- .env 自動読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。既存 OS 環境変数は保護（上書き禁止）。

### Fixed / Hardened
- run_monitoring の MONITOR_POLL_INTERVAL で不正な値（0 以下、非整数）を設定された場合に ValueError を避け、警告を出してデフォルトにフォールバックする処理を追加。
- process_priority/set_process_priority は権限不足や未対応環境での例外を捕捉して警告を出し、プロセスを強制終了しないようにした。
- init_monitoring_db を run_execution/run_monitoring 起動時に必ず呼び出し、監視テーブルが存在しない場合の起動失敗を防ぐ（冪等な初期化）。

### Security
- .env の取り扱いに関する注意書きを config_setup に明記（.env を絶対に Git にコミットしない旨）。

---

注:
- 上記はソースコードから推測できる機能・変更点を基に作成した CHANGELOG です。実際のコミット履歴（個別のバグフィックスや細かい履歴）は含まれていません。必要であれば、各モジュールごとにより詳細な変更点や既知の制約（TODO）を追加できます。
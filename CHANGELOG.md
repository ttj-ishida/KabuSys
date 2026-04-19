CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
重要: 本ファイルはコードベースから推測して作成したものであり、実際のリリースノートと差異がある可能性があります。

Unreleased
----------

- なし（今後の変更をここに記載してください）。

0.1.0 - 初期リリース
-------------------

Added
- 基本パッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。
- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と完全分離する設計。
    - BrokerClientFactory を用いて実行時に適切なブローカークライアントを生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による外部停止制御をサポート。
    - PID ファイル（data/execution.pid）を取り扱う仕組みを導入。
  - run_monitoring.py：SystemMonitor ポーリングループの起動エントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視 DB は常に同一の本番パスを参照する仕様）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。

- 設定管理
  - config.py：Settings クラスを追加し、環境変数から設定を取得する仕組みを提供。
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得用の _require() を提供（未設定時は ValueError）。
    - 各種プロパティを提供（J-Quants・kabu API・LINE・DB パス・監視閾値・環境判定など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - paper_sqlite_path（Paper Trading 用 DB）や pid/kill flag 等のパス設定を提供。
  - config_setup.py：対話式 .env 設定ウィザードを追加。
    - .env の初期作成・更新を支援。シークレット項目はマスク表示。
    - デフォルト値・選択肢・説明付きでユーザに入力を促す。
    - ファイル出力は .env を上書きし、注意文を付与。
  - validate_config.py：起動前設定検証 CLI を追加。
    - 必須環境変数未設定やプレースホルダ値の検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が利用可能な場合）等を行う。
    - --strict オプションで警告も FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）。

- ロギング / 運用ユーティリティ
  - utils/logging_setup.py：統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。LOG_LEVEL / LOG_DIR の解決順を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみを利用。
  - utils/process_priority.py：プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level) で Windows / POSIX を吸収して優先度を設定（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定する機能を実装（未指定は変更なし）。
    - 権限不足や未対応環境は警告を出してスキップ。
    - 起動スクリプトでは開始直後に set_process_priority("high") を呼び出すようにしている。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：
    - select_candidates：BUY シグナルのスコア降順ソート（タイブレークは signal_rank）と上位 N 選出。
    - calc_equal_weights：等金額配分を計算。
    - calc_score_weights：スコア加重配分を計算。全スコアが 0 の場合は等金額配分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py：
    - apply_sector_cap：既存保有のセクター別エクスポージャーを評価し、セクター上限（max_sector_pct）を超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：market レジームに基づく投下資金乗数を提供（bull/neutral/bear のマッピング、未知のレジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py：
    - calc_position_sizes：等金額・スコア基準・リスクベース（risk_based）の各方式で発注株数を計算。
      - risk_based: risk_pct や stop_loss_pct に基づきポジションサイズを算出。
      - lot_size（単元株）に基づく丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）や cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
      - スケーリング後の端数配分は fractional remainder に基づき再配分するアルゴリズムを持つ。

- 監視 / 実行の監査データベース初期化
  - monitoring/monitoring_db.init_monitoring_db を使用して起動時に監視テーブルの存在を保証（冪等）。

- ツール
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した Paper Trading DB から統計を集計し、稼働率、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ (--from / --to) をサポート。データ欠損時は N/A を表示。

- 研究用 / ファクター計算
  - research/factor_research.py：DuckDB を使ったファクター計算モジュール（Momentum / Value / Volatility / Liquidity 等の計算を想定）。
    - calc_momentum 等の関数設計開始（prices_daily / raw_financials テーブル参照、結果は (date, code) ベースの dict リストで返却）。

Changed
- なし（初期リリースのため全て追加）。

Fixed
- 不正な MONITOR_POLL_INTERVAL 値に対して明示的にフォールバックする実装を追加（run_monitoring._get_poll_interval）。0以下や非整数が指定された場合、警告を出してデフォルト 60 秒を使用。
- run_execution/run_monitoring の停止フラグ検出ロジックとリソースクリーンアップを確実にするための finally ブロックやスレッド join の追記。

Security
- .env の扱いに関する注意を config_setup の冒頭に明示（.env を Git にコミットしない旨を記載）。

Notes / Implementation details
- .env 自動ロード: プロジェクトルートが特定できない場合は自動ロードをスキップするため、配布後の環境でも安全に動作する設計。
- config_setup と validate_config により、開発者が起動前に環境変数や YAML 設定の妥当性を容易に確認できるようにしている。
- Logging: stdout を StreamHandler に用いることで cron / Task Scheduler などの運用で stdout/stderr を意識したリダイレクト運用に配慮。
- process_priority と CPU affinity は権限や OS に依存する操作であるため、失敗時は警告を出して続行する非破壊的な挙動を採用。

---

作成者注:
- 上記は提供されたソースコードから推測してまとめた CHANGELOG です。実プロジェクトのコミット履歴やリリース日付、作業者などのメタ情報は含めていません。必要であれば、各セクションに詳細（担当者／チケット番号／日付）を追加できます。
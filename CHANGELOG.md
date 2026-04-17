# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
以下の内容は提供されたコードベース（src/ 以下の実装）を元に推測して作成した CHANGELOG です。

なお、バージョン情報はパッケージの __version__ (0.1.0) を基にしています。

## [0.1.0] - 2026-04-17
初回リリース（コードベースの現状を反映）

### 追加 (Added)
- 全体
  - 初期リリースとして基本的な自動売買／検証基盤を実装。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。

- 設定・環境読み込み
  - Settings クラスを実装し、環境変数経由で各種設定（J-Quants, kabu API, DBパス, モニタ閾値 等）を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサ実装: export プレフィックス、クォート（シングル／ダブル）、エスケープ、およびコメント処理に対応。
  - 環境変数読み込み時の上書き保護機構（protected set）をサポート。

- 設定ツール / 検証
  - config_setup CLI を追加（対話式ウィザードで .env を生成／更新）。
    - 複数項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LINE トークン等）の対話入力をサポート。
    - シークレット項目のマスク表示、選択肢・デフォルト提示、保存確認を実装。
  - validate_config CLI を追加（起動前に .env と config/*.yaml の検証を実行）。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、YAML パース検証（PyYAML が存在する場合）、本番環境向けの追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- 実行エントリ / 監視
  - run_execution スクリプトを追加（ExecutionEngine 起動スクリプト）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live に応じた実装を想定）。
    - OrderRepository, OrderManager, RiskManager（RiskConfig のデフォルト値を設定）, Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を取り扱う。
  - run_monitoring スクリプトを追加（SystemMonitor ポーリングループ起動）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動（Settings を利用）。
    - 停止フラグ検知でループを終了、例外発生時はログ出力して次回ポーリングへフォールバック。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。

- 監視 DB / 初期化
  - run_* スクリプトは起動時に init_monitoring_db(sqlite_conn) を呼び監視用テーブルの存在を保証（冪等に初期化）。

- DuckDB 統合
  - DuckDB 接続を用いる設計を採用（Settings.duckdb_path）。解析処理や ExecutionEngine の解析用コネクションとして利用。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選抜（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分の重み生成。
    - calc_score_weights: スコアに応じた重み生成。全スコアが 0 の場合は等配分にフォールバックして警告ログを出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補を除外。既存ポジションのセクター別時価集計を実施。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームはフォールバックして 1.0 を返す）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・価格・現金等から各銘柄の発注株数を計算。allocation_method に "risk_based", "equal", "score" をサポート。
    - risk_based: ポジションごとのリスク許容（risk_pct, stop_loss_pct）に基づく算出。
    - lot_size（単元）に合わせた丸め、per-stock cap（max_position_pct）適用、aggregate cap（available_cash）でのスケーリングと残差分の配分ロジックを実装。cost_buffer による保守的見積もりを考慮。

- 研究／ファクター計算
  - research.factor_research
    - calc_momentum: DuckDB の prices_daily テーブルを用いて mom_1m/3m/6m と MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: ATR 20 日、相対 ATR、20 日平均売買代金、出来高比率等を計算。真の range 計算で NULL 伝播を考慮。
    - 計算用のウィンドウ／スキャン日数は定数化されており、営業日ベースのウィンドウを想定。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity: 指定コア数分だけ CPU affinity を固定する関数を用意（利用可能なコア数を超える場合の扱い、エラー時の安全なフォールバック）。
  - 停止・キルフラグ（KILL_FLAG_PATH / stop_requested.flag）の取り扱いが run スクリプトに実装。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを出力。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を実施。
    - P95 計算のユーティリティ実装。

### 変更 (Changed)
- （初回リリースなので変更履歴なし）

### 修正 (Fixed)
- （初回リリースなので修正履歴なし）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

------

注記:
- 上記はソースコードの内容から機能・挙動を推測してまとめた CHANGELOG です。実際のリリース手順やリリース日、コミット履歴は含まれていません。必要であれば、実際の git 履歴や開発ログに基づく正式な CHANGELOG の生成をお手伝いします。
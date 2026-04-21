# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを利用します。

## [0.1.0] - 初回リリース
（初期実装。バージョンは package の `kabusys.__version__` に合わせています。）

### 追加 (Added)
- 全体
  - プロジェクトの初期実装を追加。
  - パッケージのバージョンを `0.1.0` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper-trading 用の専用 SQLite（`data/paper_trading.db` をデフォルト）を使用する仕組みを実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler 等のコンポーネントを組み立てて ExecutionEngine を起動。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応。
    - 起動時にプロセス優先度を設定（`utils.process_priority.set_process_priority` を呼出し `"high"` を指定）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB（SQLite）は監視用テーブルを初期化（`init_monitoring_db`）して起動。Monitoring 実行時は環境にかかわらず本番用 `sqlite_path` を参照する設計。
    - 停止フラグ検知でループを終了する仕組みを実装。
    - エラー時は例外をキャッチしてログ出力後に次ポーリングまで待機。

- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数経由で設定を取得する統一インタフェースを提供。
    - 自動 .env 読み込み機能（プロジェクトルート検出による `.env` / `.env.local` 読み込み）を実装。OS 環境変数の保護（上書き保護）に対応。
    - .env パースは export 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどを考慮した堅牢な実装。
    - 各種設定プロパティを実装（J-Quants / kabu API / LINE / DB パス / paper trading / 監視閾値 / env/log level 判定 等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 必要項目（J-Quants トークン、kabu API パスワード等）とデフォルト値、説明文を提示して .env を生成。
    - シークレット項目は出力時にマスク表示（セキュリティ配慮）。
    - 生成した .env の保存確認とファイル書き込みを実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV 値・ログレベル・DB パスの親ディレクトリ存在確認・config/*.yaml ファイルの存在と YAML パース検証（PyYAML が利用可能な場合）などをチェック。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）用の追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等分配にフォールバックし、警告ログを出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) とレジーム乗数計算 (calc_regime_multiplier) を実装。
    - セクター上限超過銘柄の除外ロジック、未知レジームのフォールバック、ログ出力を含む。

  - portfolio/position_sizing.py
    - 発注株数計算 (calc_position_sizes) を実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元株丸め（lot_size）、per-asset 上限（max_position_pct）、全体投下上限（available_cash による aggregate cap）およびコストバッファの考慮、スケーリングと残差配分ロジックを実装。
    - price 欠損時のスキップやログ出力など堅牢性を配慮。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリで共通に使えるログ設定ユーティリティを実装。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリアやディレクトリ作成失敗時のフォールバックに対応。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。
    - Windows / POSIX（Linux, macOS, FreeBSD）を抽象化して適切な優先度設定を行い、権限不足や非対応環境では警告ログでスキップ。
    - psutil 依存だが、存在する定数を getattr で安全に参照する実装。

- 監視・レポート
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などのテーブルを参照し、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し PASS/FAIL を判定するレポートを出力。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - P95 計算、NULL/データ欠損時の N/A 出力、閾値を超えた場合の失敗理由列挙などを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - ファクター計算モジュールの雛形を追加（モメンタム、MA200 乖離、ATR、流動性等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計を採用。
    - （注）ファイルの最後で calc_momentum の実装開始が見られるが、ソースは途中で切れており未完の部分が残る（詳細は既知の問題参照）。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- .env パーサーで以下のケースに対応して堅牢性を向上：
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い。
  - .env のロード順序や OS 環境変数の保護（`.env.local` は上書き可能だが OS 環境変数は保護）を明確化。

### 既知の問題 (Known issues)
- research/factor_research.calc_momentum の実装が途中で切れている（ソース末尾が未完）。ファクター計算の完全実装は今後のタスク。
- 一部 TODO コメント（例: position_sizing の lot_size を銘柄毎に持たせる等）が残っており、将来的な拡張が想定される。
- ログディレクトリ作成やプロセス優先度設定は環境・権限に依存するため、失敗時はフォールバックするが、運用上の注意が必要。

### セキュリティ (Security)
- config_setup の対話出力ではシークレット値をマスクして表示することで、画面上での露出を軽減。
- .env は Git にコミットしないよう README / .env ヘッダに注意書きを追加（config_setup の生成ヘッダに記載）。

---

今後の予定（例）
- factor_research の完成、ユニットテスト追加、CI / ドキュメント整備。
- ExecutionEngine / SystemMonitor の詳細なテストと障害対応の強化。
- 銘柄ごとの lot_size 対応や手数料・スリッページの実運用パラメータ改善。
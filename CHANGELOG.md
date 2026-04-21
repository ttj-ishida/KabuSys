# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの __version__ に基づきます。

## [Unreleased]

（現在の差分は特になし。必要に応じてここに記載してください）

---

## [0.1.0] - 初期リリース

初回公開リリース。以下の主要機能・ユーティリティ・CLI を実装しています。

### Added

- 実行/監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
    - stop フラグファイル(data/stop_requested.flag) による安全な停止処理を実装。
    - エンジンは別スレッドで実行し、停止フラグ検知でエンジン.stop() を呼び安全終了を試みる。
  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はログ出力のうえデフォルトへフォールバック。
    - 監視は環境にかかわらず本番（settings.sqlite_path）を使用する設計。
    - stop フラグファイル検知でループを終了する。

- 設定管理（config）
  - Settings クラスを提供し、環境変数から各種設定を取得するユーティリティを実装。
  - .env 自動読み込み:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む。OS 環境変数は保護され、.env.local は上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 環境変数パースの堅牢化:
    - export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、行内コメント処理などに対応。
  - 多数のプロパティ実装（J-Quants、kabuステーション、LINE、DB パス、監視閾値、環境判定など）。
  - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）。

- 設定関連 CLI / ユーティリティ
  - config_setup.py
    - 対話式ウィザードで .env を新規作成／更新する CLI を実装。
    - シークレット値はマスク表示、選択肢・デフォルト提示、確認プロンプトなどを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML 利用時のパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や Kill Switch 関連の警告）を行う。
    - --strict オプションで警告も FAIL 扱い（exit 1）。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - すべての起動スクリプトで共通利用するログ初期化関数を提供。
    - StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次ローテーション・30 日保持）でファイル出力を行う（ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ）。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを提供（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を実装。
    - アクセス権限や未対応 OS の場合は警告ログでスキップ。

- 発注・実行関連（Execution）
  - BrokerClientFactory により環境に応じた BrokerClient を生成（paper/live の切替を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine といった実行に必要なコンポーネント群を組み立て、エンジン実行ロジックを統合（コード内設定でリスク閾値等を初期化）。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計レポートを生成する CLI を実装。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - P95 計算実装、閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定。
    - 日付フィルタ（--from/--to）や --db オプションをサポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのスコア降順選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights; スコア合計が0の場合に等分配へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用して候補を除外する apply_sector_cap を実装（"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マップ、未知レジームは警告のうえ 1.0 をフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based","equal","score"）に基づく株数決定を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリング処理を実装。
    - 利用可能現金を超過した場合のスケールダウンおよび残余キャッシュを用いた端数補正ロジックを実装。

- リサーチ基盤（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨組み（モメンタム、MA200、ATR、流動性など）を実装。DuckDB 接続を受けて prices_daily / raw_financials から計算する設計。
    - モメンタム計算の定数（期間・スキャン範囲）等を定義（関数群は継続実装予定）。

- パッケージ定義
  - パッケージメタデータにバージョンを追加（kabusys.__init__.__version__ = "0.1.0"）。

### Changed

- 設計決定
  - 監視（monitoring）は環境変数に依存せず常に本番用 sqlite_path を参照するように設計（監視対象は本番リソースを想定）。
  - ログ出力は標準出力を stderr ではなく stdout に出すよう統一（タスクスケジューラや cron でのリダイレクトを想定）。
  - .env の読み込み順序は OS 環境 > .env.local > .env（.env.local は上書き可能）で統一。

### Fixed

- 環境変数パースの安定化
  - .env 内のクォート付き値でのバックスラッシュエスケープや行末コメントの取り扱いを改善し、意図しないコメントの取り込みやクォート閉じ忘れによる解析ミスを低減。
- ポーリング間隔の検証
  - MONITOR_POLL_INTERVAL の不正値（0 以下、非整数）を検出して警告を出し、デフォルト値へフォールバックするように修正（time.sleep に渡す値が不正な場合のクラッシュを回避）。

### Notes / Caveats

- 一部モジュール（factor_research など）は計算ロジックの全実装が継続中であり、DuckDB 上のテーブル名（prices_daily, raw_financials）に依存します。実行環境では該当テーブルが存在することを確認してください。
- process_priority の設定や CPU affinity の操作は権限や実行環境に依存します。パーミッションや OS の制約により設定に失敗する場合は警告ログを出力してスキップします。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きを記載）。

---

本 CHANGELOG はコードベースの実装内容から推測して作成しています。必要に応じてリリースごとに差分を具体的なコミット/チケット等と紐づけて更新してください。
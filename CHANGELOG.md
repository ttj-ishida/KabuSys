# CHANGELOG

すべての注記は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
最初の公開リリース。自動売買システムのコア機能、運用用スクリプト、ユーティリティ、検証ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用し、本番 DB と分離して動作。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - デフォルトポーリング間隔は 60 秒で、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバック）。
    - 監視は常に本番用の sqlite_path を使用（環境に依らず監視 DB を共通化）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt を適切にハンドリング。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装。
    - .env 読み込みは OS 環境変数を保護しつつ `.env` と `.env.local` を順次適用。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 複数の便利プロパティを提供する `Settings` クラス（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境判定 等）。
    - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - `env` / `log_level` のバリデーションと `is_live` / `is_paper` 等の判定ヘルパー。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を実装。
    - デフォルト値・選択肢・シークレット入力対応。既存 .env の読み込みと Enter による再利用をサポート。
    - 出力は .env に書き込み、次に validate_config の実行を推奨。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml（存在する場合）を起動前に検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML の有無に応じてスキップや警告）など。
    - `--strict` オプションで警告も失敗扱いにできる。

- 運用／報告ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを算出し、閾値（稼働率 99% 等）による PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）と `--db` オプションをサポート。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークは signal_rank）。
    - 等配分およびスコア加重配分の重み算出（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存保有を考慮して、上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知は警告とフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate 上限・cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウン処理。
    - aggregate cap 超過時のスケーリングと残余キャッシュを活用した追加配分ロジック（再現性を保つ並び順の安定化）。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨格（Momentum / Value / Volatility / Liquidity 指標の計算方針と定数を実装）。
    - prices_daily / raw_financials テーブルのみを参照して計算する設計。Zスコア正規化などは外部ユーティリティを利用する想定。

- 監視 DB 初期化
  - monitoring/monitoring_db.py の init_monitoring_db を各起動スクリプトから利用し、監視テーブルの存在を保証。

- ユーティリティ
  - utils/logging_setup.py
    - 一元的なログ設定ユーティリティを実装（StreamHandler → stdout、TimedRotatingFileHandler による日次ローテーション、30日保持）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX を吸収してカレントプロセスの優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する関数も提供（権限不足や未サポート時は警告をログ出力してスキップ）。

### Changed
- ドキュメント的な注記を多数追加
  - 各モジュールに設計方針、使用例、注意（例: price 欠損時の TODO）を docstring レベルで明示。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックスに対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装して現実的な .env 記述をパース。
- 各起動スクリプトでの DB クローズ処理を finally ブロックで確実に行うようにしてリソースリークを防止。

### Security
- .env に含まれるシークレットは config_setup の表示でマスクする等、秘匿情報の扱いに配慮。

### Notes / Implementation details
- stop / kill フラグ
  - 実行中の停止は data/stop_requested.flag（および設定での KILL_FLAG_PATH）で行える設計。`KILL_FLAG_CLEAR_ON_START` により起動時に kill flag を自動クリアする挙動を設定可能（本番ではデフォルト 0 を推奨）。
- Paper Trading 分離
  - `paper_trading` 環境では発注やデータ記録が本番 DB と分離され、`PAPER_TRADING_SQLITE_PATH` を使って data/paper_trading.db に記録。
- ロギング
  - stdout を利用する仕様により、cron / systemd 等でのログ取り回しが容易。ファイル出力が不可でも実行継続する堅牢性を確保。
- クロスプラットフォーム対応
  - process_priority や logging の挙動は主要プラットフォーム（Windows / Linux / macOS）を想定し、未対応環境では警告を出して安全にフォールバック。

---

今後の想定追加項目（未実装だがコードから予想される拡張点）
- strategy モジュールのシグナル生成の完全実装と統合テスト
- 銘柄マスタに単元情報や銘柄別 lot_size を持たせる拡張
- factor_research の完全実装（Value / Volatility / Liquidity の SQL 実装および正規化）
- GUI/ダッシュボードや Prometheus Exporter の追加検討

==============================================================================

上記はリポジトリ内のコード・コメント・ドキュメント文字列から推測してまとめた CHANGELOG です。必要があれば各項目の詳細化（例: 使用例、エラーコード、既知の制約）も追記します。
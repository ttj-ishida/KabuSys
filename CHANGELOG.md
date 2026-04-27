# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

注: 以下の履歴は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-27

初回リリース。自動売買システム KabuSys の基礎となるコマンドラインエントリポイント、設定管理、レポート生成、検証ツールを実装しました。

### Added
- 実行系・監視系エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、paper_trading 用に分離された SQLite（デフォルト: data/paper_trading.db）を利用する実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 起動時総資産（現金 + 保有評価額）を計算し、Execution Startup Summary を生成・表示・保存する機能を追加。
    - リコンシリエーション（Reconciler）を実行し、結果に応じて ExecutionEngine を組み立て・起動。
    - data/stop_requested.flag による起動抑止・実行中停止フラグの検出とグレースフル停止対応。
    - PID ファイル出力（data/execution.pid 等）対応。
    - risk_config.yaml を読み込み、値のバリデーション（範囲チェックや必須キーチェック）を行うロード機能を実装。読み込み・パースエラーに対する明示的なエラーメッセージを追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を上書き可能（不正値は警告を出してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する挙動を採用。
    - 初期化で監視用 DB テーブルを作成（init_monitoring_db）し、duckdb と sqlite の接続を確立。
    - 停止フラグ検出と例外安全なループ運用、キーボード割り込みのハンドリングを実装。

  - run_signal_queue_report.py
    - Signal Queue Confirmation View の CLI を追加。
    - オプション: --date（対象日指定）, --save（artifacts に保存）, --json（JSON 出力）。
    - DuckDB から signals / portfolio_targets を集計し、READY/EMPTY の判定とシグナル一覧を出力。終了コードはレポートステータスに依存。

  - run_pre_market_report.py
    - Pre-Market Report の CLI を追加。
    - duckdb + sqlite（読み取り専用）からデータ収集を行い、前場開始前の健全性指標を出力。--save/--json オプションに対応。BLOCKED 状態のときは非ゼロ終了。

- 設定管理 / 初期化
  - config.py
    - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ファイルのパーサーを強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 環境変数上書き時の protected（OS 環境変数保護）をサポート。
    - Settings クラスを実装し、各種設定値（J-Quants, kabuAPI, LINE, DB パス, kill flag 等）をプロパティ経由で取得・検証。KABUSYS_ENV / LOG_LEVEL の値検証、paper_fill_mode の有効値チェックなどを実装。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - デフォルト値、選択肢、シークレット項目のマスク表示、保存プレビュー、.env の書き込み機能を提供。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、placeholder 値検出、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス親ディレクトリの存在確認、PyYAML があれば YAML パース検証を実行。
    - 本番環境（KABUSYS_ENV=live）向けのガードチェック（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。
    - --strict オプションで警告を失敗扱いにする機能を追加。

- レポート / ツール
  - operations/signal_queue_report.py
    - DuckDB から当日（または指定日）のシグナルを収集する collect_signals() を実装。
    - SignalQueueReport データ構造と build_report()、CLI / JSON / Markdown 用フォーマッター、artifacts への保存機能を実装（保存先: artifacts/signal_queue/{date}/）。
    - signals と portfolio_targets の LEFT JOIN、警告生成（BUY で target_size 未設定等）を実装。

  - operations/execution_startup_report.py
    - ReconcileResult から ExecutionStartupReport を生成する純粋関数を実装。
    - READY / READY_WITH_WARNINGS / BLOCKED の判定ロジックを実装（orders_no_status がある場合は BLOCKED、位置差分のみは READY_WITH_WARNINGS）。

  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - P95 の計算、閾値判定（稼働率/成功率/送信率/P95）に基づく PASS/FAIL 出力を実装。

### Changed
- DB 関連の振る舞いを明確化
  - 監視 (run_monitoring) は常に本番 sqlite_path を参照する仕様を採用（環境に依存しない監視データの一元化）。
  - paper_trading 環境では Execution は paper_sqlite_path を使用して本番 DB と完全に分離。

- 安全性・堅牢性の向上
  - 各 CLI / エントリポイントでの例外ハンドリングやリソースクリーンアップ（sqlite/duckdb コネクションの確実な close）を追加。
  - run_execution の起動時に監視テーブルの存在を保証するため init_monitoring_db を冪等で呼び出すようにした。

### Fixed
- .env パーサーの改善により、引用符やエスケープ・インラインコメントの扱いでの誤解析を修正。
- risk_config の読み込みでのエラー文言と例外の明示化により、設定ミス時に復旧手順が分かりやすくなった。

### Security
- シークレット扱いの設定（トークン・パスワード）を対話式ウィザードでマスク表示する等、取り扱いに配慮。

---

開発・運用に関する注記:
- 多くの機能は環境変数や設定ファイル（config/*.yaml）に依存します。デプロイ前に config_setup と validate_config を実行して設定を確認してください。
- 本番環境では KILL_FLAG_CLEAR_ON_START をデフォルト 0 にして、誤って Kill Flag を自動クリアしない運用を推奨します。
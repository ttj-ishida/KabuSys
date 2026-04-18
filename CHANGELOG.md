# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース履歴:

## [0.1.0] - 2026-04-18

### Added
- プロジェクト初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 自動読み込みと Settings クラス（バリデーション付き）。
      - プロジェクトルート自動検出（.git または pyproject.toml 基準）。
      - .env / .env.local の読み込みロジック（export 形式やクォート処理、コメント処理に対応）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - Settings プロパティ群（J-Quants / kabuステーション / DB パス / 監視閾値 / 環境判定など）を提供。PAPER_FILL_MODE や KABUSYS_ENV の値検証を実装。
    - 起動スクリプト:
      - run_execution.py: ExecutionEngine 起動スクリプトを追加。
        - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を利用（本番 DB と完全分離）。
        - BrokerClientFactory を利用してブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
        - 停止フラグ（data/stop_requested.flag）および PID ファイル管理をサポート。
        - RiskManager のデフォルト設定を含むリスク制御パラメータを初期化。
      - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
        - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
        - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
        - 停止フラグ検知・例外発生時のログ出力・duckdb/SQLite のクリーンなクローズ処理を実装。
  - 監視関連:
    - kabusys.monitoring.monitoring_db との初期化接続フローを組み込み（init_monitoring_db 呼び出し）。
    - duckdb 接続を利用した分析データ基盤と統合。
  - ポートフォリオ構築（純関数群）:
    - portfolio.portfolio_builder:
      - select_candidates: シグナルのスコアでソートして上位 N 件を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクターエクスポージャを計算し、新規候補を除外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知は警告して 1.0 にフォールバック）。
    - portfolio.position_sizing:
      - calc_position_sizes: risk_based / equal / score の割当方式をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリングと端数処理（残差に基づく追加配分）を実装。
  - ユーティリティ:
    - utils.logging_setup: ルートロガー設定ユーティリティ。
      - stdout（StreamHandler）と日次ローテートするファイル（TimedRotatingFileHandler）を設定。
      - LOG_DIR / LOG_LEVEL 解決順やログディレクトリ作成失敗時のフォールバックを備える。
    - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティ（psutil 利用）。
      - Windows / POSIX（Linux/Mac/FreeBSD）に対応する実装。権限不足や未対応 OS の場合は警告してスキップ。
  - 開発支援ツール:
    - validate_config.py: .env と config/*.yaml の設定検証 CLI。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの存在確認、YAML パース（PyYAML 未インストール時は警告してスキップ）、本番環境時のガードチェックを実装。
      - --strict フラグで警告も失敗扱いにできる。
    - config_setup.py: .env の対話式ウィザード（初期作成・更新）。
      - 複数項目の対話入力、既存 .env 読み込み、秘密値マスク、保存前の確認を実装。
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定。
      - CLI 引数で期間指定（--from / --to）および DB パスの上書き（--db）をサポート。
      - デフォルト閾値（稼働率 99% / 成立率 90% / 送信率 95% / P95 レイテンシ 200ms）を定義。
  - research.factor_research（着手中）: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等を計算する関数を実装予定、ファイル末尾で実装途中の状態）

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Notes / Implementation remarks
- 設定ファイル（config/*.yaml）や .env の書式・存在チェックは validate_config で事前に確認することを推奨。
- run_monitoring は運用上の注意として「監視は常に本番の sqlite_path を使う」設計になっているため、テスト目的で監視 DB を分離したい場合は別途考慮が必要。
- run_execution は paper_trading モードで paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番データと分離する設計。
- いくつかの箇所に TODO / 注意コメントあり（例: price が欠損した場合のフォールバック等）。運用時はこれらの点を確認・拡張することを推奨。

### Security
- .env は絶対にリポジトリにコミットしない旨を config_setup の生成ファイルヘッダに明記。

---
今後の予定:
- research.factor_research の完全実装（ファクター計算の SQL/処理完成）。
- Strategy / Execution の統合テストとエラーケースの追加ハンドリング。
- 単体テスト・CI の整備（現状は実装コードベースのみ）。
CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式で記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース: KabuSys の基本機能群を実装。
  - ポートフォリオ構築
    - 銘柄選定/スコアソート: select_candidates（score/順位によるタイブレーク実装）
    - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が0の場合は等配分へフォールバック）
    - セクター制限・レジーム調整: apply_sector_cap（セクター上限適用、"unknown" セクターは除外対象外）、calc_regime_multiplier（bull/neutral/bear の乗数）
    - ポジションサイズ算出: calc_position_sizes（risk_based / equal / score 対応、単元株（lot_size）丸め、aggregate cap によるスケーリング・端数配分ロジック）
  - 実行エンジン関連
    - エントリポイント: run_execution.py
    - BrokerClientFactory 経由でブローカークライアントを選択（KABUSYS_ENV=paper_trading 時はモック使用、paper_trading 用 SQLite を分離）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行ループ（バックグラウンドスレッド起動、停止フラグ監視）
    - 実行用 PID ファイル・停止フラグ処理（data/execution.pid, data/stop_requested.flag）
  - 監視（Monitoring）
    - エントリポイント: run_monitoring.py（SystemMonitor のポーリングループ）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）
    - 監視用 DB 初期化（init_monitoring_db）を idempotent に保証
    - 監視は環境に関わらず本番 sqlite_path を使用する挙動
  - 設定・CLI
    - Settings クラスによる環境変数ラッパー（各種デフォルト、型変換、妥当性チェックを実施）
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。.env と .env.local の読み込み順序を実装。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
    - 対話式設定ウィザード: config_setup.py（.env の初期作成/更新、シークレットのマスク表示）
    - 設定検証ツール: validate_config.py（必須環境変数チェック、ログレベル/パス/構成ファイルチェック、--strict オプション）
  - ツール
    - paper_verification_report.py: Paper Trading の検証レポート生成（稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等）。PAPER_TRADING_SQLITE_PATH の指定対応、日付フィルタ対応
  - ユーティリティ
    - logging_setup.py: 統一ログ設定（コンソール stdout と TimedRotatingFileHandler を設定、ログディレクトリ作成失敗時はファイル出力をスキップ）
    - process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）、CPU affinity 設定ユーティリティ（psutil 必須、権限不足時は警告）
  - リサーチ / ファクター計算の骨格
    - factor_research.py: DuckDB を使ったファクター計算（モメンタム/MA/ATR 等を想定）。（ファイルは部分実装）

Changed
- 新規リリースのため該当なし

Fixed
- .env パーサーの堅牢化:
  - export KEY=val 形式、クォート文字列中のエスケープ、インラインコメントの扱いなどを考慮して安全にパースする実装を導入
  - コメント扱い（クォートなしで '#' の直前がスペース/タブ の場合のみコメントとみなす）により既存の .env 慣習に合わせた処理
- ロギング: ログディレクトリ作成に失敗した場合でもコンソールログで継続するフォールバックを実装（運用時の致命的障害を回避）
- DB 初期化: monitoring 用 DB の初期化は冪等に行う（存在確認して必要なら作成）

Security
- 特筆すべきセキュリティ修正は無し。ただし .env は絶対にリポジトリにコミットしない旨を config_setup のヘッダに明示

Notes / Known issues
- calc_position_sizes / apply_sector_cap 等いくつかの箇所に将来の拡張メモ（例: 銘柄ごとの lot_size の導入、価格欠損時のフォールバック）が残っている（TODO コメントあり）
- プロセス優先度設定や CPU affinity は OS 権限に依存し、権限不足時は警告を出してスキップする（動作保証は環境依存）
- factor_research.py はファクター計算方針を示しているが一部未完（ファイル末尾が切れているため実装の追加が必要）

参考
- パッケージバージョン: __version__ = "0.1.0"
- 主要環境変数とデフォルト:
  - KABUSYS_ENV: development (valid: development, paper_trading, live)
  - SQLITE_PATH: data/monitoring.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - MONITOR_POLL_INTERVAL: 60 (秒)
  - LOG_DIR: logs/（デフォルト）
  - LOG_LEVEL: INFO（変更可能）

----------
（この CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリースの事実・日付・コミット等に基づいて適宜調整してください。）
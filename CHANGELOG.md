CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
タグ付けは semantic versioning に従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
-----
- 基本パッケージと CLI/ユーティリティ群を初期実装として追加。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視ループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止制御はプロジェクトルート/data/stop_requested.flag による。
    - Monitoring は KABUSYS_ENV の値に関わらず本番用 sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離する設計。
    - 停止用フラグ（data/stop_requested.flag）検知で安全に停止する機能を搭載。
    - 実行時に data/execution.pid を利用（PID ファイルパス）。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local、OS 環境変数優先）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの挙動（export 対応、クォート・エスケープ、インラインコメント処理）を実装。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティで取得可能。
    - PAPER_FILL_MODE の有効値検証（"instant"|"partial"|"never"|"reject"）。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援。
    - J-Quants / kabu API 等の必須項目やデフォルト値を対話的に設定可能。
  - validate_config.py
    - .env および config/*.yaml の起動前チェックツール。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性確認、YAML の存在/パース確認（PyYAML に依存）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを実装。
    - stdout 出力（StreamHandler）と日次ローテート（TimedRotatingFileHandler、デフォルト logs/<app>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - LOG_LEVEL / LOG_DIR など環境変数で挙動を制御可能。
- プロセス優先度・CPU 固定
  - utils/process_priority.py
    - Windows / POSIX に対応したプロセス優先度 (high/normal/low) 設定。
    - CPU affinity 固定機能（最初の N コアに固定）を提供。
    - 権限不足や未サポート環境時は警告ログを出してフォールバックする実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を提供。
    - score が全て 0 の場合は等分配にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を提供。
    - 未知レジーム時はフォールバック挙動（1.0）で警告。
  - portfolio/position_sizing.py
    - 各配分方式（risk_based、equal、score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限 (max_position_pct)、投下上限 (max_utilization)、コストバッファ考慮によるスケーリング機能を備える。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading DB（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等のレポートを生成。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - DB が存在しない場合に分かりやすいエラーメッセージを出力。
- Execution 内コンポーネント組み立て（実行時）
  - run_execution は BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて起動するフローを実装。
  - RiskManager の既定値（max_position_pct=0.20 等）と、initial_portfolio_value を broker.get_available_cash() から取得する設計。

Changed
-------
- 初期リリースのため該当項目なし。

Fixed
-----
- 初期リリースのため該当項目なし。

Deprecated
----------
- 初期リリースのため該当項目なし。

Removed
-------
- 初期リリースのため該当項目なし。

Security
--------
- 初期リリースのため該当項目なし。

Notes / 運用メモ
----------------
- デフォルトのファイルパス
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / stop フラグ類: data/*.pid, data/stop_requested.flag
  - ログ: logs/<app_name>.log（デフォルト）
- .env 自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml を基準）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必須（validate_config で検査）。
- run_monitoring は環境に関わらず monitoring 用 DB に本番 sqlite_path を使用する点に注意してください（設計上の意図）。
- Paper Trading 実行時は run_execution が paper_trading 用 DB に接続することで本番 DB と分離されるようになっています。

今後の改善候補（実装メモ）
-------------------------
- position_sizing の lot_size を銘柄別に持てるよう拡張（stocks マスタから取得）。
- sector_exposure 計算で価格欠損時のフォールバック（前日終値等）を追加。
- factor_research モジュール（ファクター計算群）の実装・テストの継続（duckdb を使った計算ロジックの完成）。
- より詳細な E2E テスト（mock broker の挙動検証、stop フラグ/kill フラグの統合テスト）。


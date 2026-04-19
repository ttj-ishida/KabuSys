CHANGELOG
=========
すべての変更は "Keep a Changelog" のフォーマットに従って記載しています。  
日付はコードスナップショットを基に推定しています。

[Unreleased]
-------------
- なし

[0.1.0] - 2026-04-19
--------------------
初期リリース（コードベースの機能をまとめて記載）。主に自動売買システムの起動 / 設定 / ポートフォリオ構築 / ユーティリティ類を含みます。

Added
-----
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db のデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して実運用／モックの切替を実装。
    - 実行時にプロセス優先度を high に設定するフローを導入。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用した安全な起動／停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。

- 設定関連
  - config.py
    - 環境変数および .env ファイル読み込みロジックを実装。
    - プロジェクトルート自動探索（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動ロードを実現。
    - .env 行のパースで export プレフィックス、クォート内のバックスラッシュエスケープ、コメント処理などを考慮する堅牢な実装を追加。
    - Settings クラスを提供し、J-Quants / kabuステーション / DB パス / 各種閾値（CPU/MEM/DISK）や環境種別判定（is_live/is_paper/is_dev）などのプロパティを集中管理。
    - PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH 等、paper_trading に関する設定も取り扱う。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能。

  - config_setup.py
    - 対話式の環境設定ウィザードを追加 (.env の初期作成・更新を支援)。
    - デフォルト値・選択肢・シークレット入力対応・既存 .env 読み込みと保存処理を実装。
    - 保存前の確認・キャンセルをサポート。

  - validate_config.py
    - 起動前に .env および config/*.yaml の基本的な妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の値チェック、LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース（PyYAML があれば検証）などを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築 / リスク管理（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるフィルタ（当日売却予定の除外などのオプションあり）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・資産・現金・既存ポジション・価格・各種制約（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を考慮して発注株数を算出。
    - lot_size（単元株）に合わせた丸め、コストバッファを考慮した保守的見積り、集計キャップ超過時のスケーリングと残余配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化ユーティリティを追加（setup_logging）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する耐障害設計。
    - LOG_LEVEL / LOG_DIR の解決順を明示。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定を実装（Windows の優先度クラス、POSIX の nice 値を適用）。
    - CPU affinity を最初の N コアに固定するユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 監視・データベース
  - monitoring_db 初期化呼び出しを起動スクリプトで実行（init_monitoring_db を利用）して監視テーブルの存在を保証。
  - run_monitoring/run_execution で DuckDB と SQLite の両方に接続する構成を採用（duckdb は分析用、sqlite は監視・注文履歴用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 を含む）等を集計し、PASS/FAIL 判定を行う。
    - CLI オプションで期間指定（--from/--to）と DB パス指定（--db）をサポート。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義しレポート出力。

- リサーチ（未完）
  - research/factor_research.py（ファクター計算モジュール）を追加。モメンタム等の複数ファクター算出を目的に設計されているが、ファイル末尾が途中で切れており実装は一部（未完）であることを示唆。

Changed
-------
- パッケージメタデータ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定（初期バージョン）。

Fixed
-----
- ロバスト性向上
  - .env 読み込み時のファイル読み込み失敗を警告に置き換え、起動継続できるように変更（config._load_env_file）。
  - logging_setup: ログディレクトリ作成に失敗した場合でもコンソール出力は維持する挙動により起動時の致命的エラーを回避。
  - process_priority: 権限不足や未実装関数で例外が発生しても警告で処理を継続するように変更。

Notes / Implementation details
------------------------------
- 環境ファイル (.env) の優先順位: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を提供。
- run_monitoring は MONITOR_POLL_INTERVAL に無効な値が設定された場合、警告を出してデフォルト（60 秒）にフォールバックする。
- Execution 側は paper_trading と本番の DB を明確に分離しており、paper_trading モードでは MockBroker を使って記録先 DB を分ける設計になっている（データ分離を想定）。
- portfolio モジュール群は副作用を持たない「純粋関数」設計で、外部 DB 参照を行わずメモリ内計算のみで動作するように設計されている。
- research/factor_research.py は設計注記（対象ファクター、ウィンドウ長など）を含むが、ファイルの最後が切れているため実装は継続が必要。

Security
--------
- .env ファイルは Git にコミットしないよう README 等で注意する旨の注釈（config_setup のヘッダ）を追加。

---
今後の推奨
- research/factor_research.py の未完部分の実装完了。
- 各モジュールに対する単体テストおよび統合テストの整備（特に position sizing / scaling / sector cap の境界ケース）。
- ロギング・監視まわりのメトリクス化（Prometheus 等）や、ExecutionEngine のフェイルオーバー動作の明文化。
- Paper Trading レポートの閾値や指標を設定ファイル化し、CI や Nightly レポート化する運用化。
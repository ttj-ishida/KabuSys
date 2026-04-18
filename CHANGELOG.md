CHANGELOG
=========

すべての注目すべき変更履歴を記載します（Keep a Changelog 準拠）。
このファイルは human-readable な変更履歴を目的としています。セマンティックバージョニングに従って管理してください。

v0.1.0 — 2026-04-18
-------------------

Added
- 初回リリース。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db を想定）を使用し、本番 DB と分離。
    - BrokerClientFactory により通常のブローカ実装と MockBrokerClient を切り替え可能。
    - エンジンはデーモンスレッドで実行。停止は data/stop_requested.flag により行える（PID ファイル管理もあり）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照して監視テーブルを初期化する（環境に依存しない）。
    - stop フラグ（data/stop_requested.flag）検出で安全にループ終了。
- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 独自の .env パーサ実装（export KEY=val、クォート/エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを導入し、環境変数をラップして型変換・検証を提供。
    - Paper Trading 向けの設定 (paper_sqlite_path, paper_fill_mode など) と監視閾値（cpu/memory/disk）をプロパティとして提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - デフォルト値・秘匿表示・選択肢サポート、保存前の確認を実装。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の簡易検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ確認、YAML のパース（PyYAML 利用可時）を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング周り
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリの自動作成とフォールバック（作成失敗時はコンソールのみ）に対応。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を提供。
    - アクセス権限エラーを安全に処理してフォールバックする実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順）と等金額・スコア加重配分ロジックを追加。
  - portfolio/position_sizing.py
    - 複数の割付方式（risk_based, equal, score）に対応した株数算出ロジックを追加。
    - lot_size（単元）丸め、最大ポジション比、aggregate cap（利用可能現金超過時のスケールダウン）や cost_buffer を考慮したスケーリングロジックを実装。
    - リスクベースの基本計算（許容リスク率・ストップロスを用いたポジション算出）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既知のレジーム値をマップしてフォールバックを実装。
- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
    - --from/--to/--db オプションで期間と DB を指定可能。
- 研究モジュール（下地）
  - research/factor_research.py（ファクター計算モジュールの骨組み）
    - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計。
    - モメンタム計算の定数・仕様を定義（1M/3M/6M リターン、MA200 乖離、ATR 等）。
- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Notes / 重要な運用メモ
- .env 管理
  - .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも注記）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途など）。
- 起動順序・優先度
  - run_execution/run_monitoring のいずれも起動直後にプロセス優先度を high に変更しようとします。権限がない場合は警告が出ますが処理は継続します。
- Paper Trading の分離
  - paper_trading モードは専用の SQLite ファイルを使用するため、本番データと完全に分離できます（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- 停止制御
  - 停止はプロジェクトルート下の data/stop_requested.flag により行います。PID ファイル（data/execution.pid など）も管理されます。
- 監視とレポート
  - monitoring は本番用 sqlite_path を参照してデータを記録します（環境に依存しない監視）。
  - paper_verification_report はデータが存在しない場合に N/A を表示して FAIL 判定を行います。DB の欠損やテーブル欠如を想定した安全な扱いを実装しています。

Usage examples
- 設定ウィザード（対話式で .env を生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

今後の予定（簡単なロードマップ）
- factor_research の完全実装（各ファクターの SQL 実装と z-score 正規化）
- ExecutionEngine / OrderManager / Reconciler 等の詳細実装・テストカバレッジ強化
- 冗長性・運用性向上（デーモン化 / systemd ユニット例 / コンテナ化）
- 監視アラート（LINE 通知）の拡充

--- 
（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴に基づく正確な差分が必要な場合は git の履歴から change entries を生成してください。）
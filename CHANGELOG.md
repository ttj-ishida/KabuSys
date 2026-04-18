# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません。コードベースから推測して初回リリースの変更履歴を以下に記載します）

## [0.1.0] - 2026-04-18

初回リリース。KabuSys の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### Added
- 実行・監視用起動スクリプト
  - run_execution.py
    - ExecutionEngine をデーモンとして起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を High に設定。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine.run_session をバックグラウンドスレッドで実行し、停止フラグ検知で安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトへフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは分離しない設計）。
    - プロセス優先度を High に設定、停止フラグ検知でループ終了。
- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き可能）。
    - 複雑な .env 行のパース機能（export 対応、クォート内エスケープ処理、インラインコメントの扱い）。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API、DB パス、監視しきい値、環境判定など）。
    - PAPER_FILL_MODE 検証（有効値: "instant"|"partial"|"never"|"reject"）。不正値は例外を送出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止サポート。
- 設定ツール / 検証
  - config_setup.py
    - 対話式の .env 作成ウィザード。デフォルト値・マスク表示・選択肢サポート。
    - 生成・更新された .env をファイルに書き出すユーティリティを提供。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の存在チェック、設定ファイル（config/*.yaml）の存在と（PyYAML があれば）パース検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、本番環境での追加ガード（LINE 通知設定や kill フラグ設定の警告）などを実行。
    - --strict オプションで警告も失敗（exit 1）と扱うモードを提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - score が全て 0 の場合に等金額配分にフォールバックする警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)：既存ポジションのセクター露出に応じて候補を除外するロジック。
    - レジーム乗数 (calc_regime_multiplier)：市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score 方式）、単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリングと端数配分）を実装。
    - cost_buffer を用いた保守的コスト見積りをサポート。
- ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティ（stdout StreamHandler と TimedRotatingFileHandler 日次ローテーション、既存ハンドラのクリア、ログディレクトリ作成のフェールフォールバック）。
    - LOG_LEVEL / LOG_DIR の優先解決ロジックを実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度設定（high/normal/low）を行うヘルパー。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（アクセス権限や未対応 OS の場合は警告を出力してスキップ）。
- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動時に呼び出して監視用テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ（p95 latency）などを算出。
    - 閾値による PASS/FAIL 判定を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from / --to）、DB 指定（--db）をサポート。
    - レイテンシ P95 は独自計算を実装（サンプルが空の場合は N/A）。
- 研究用ファクター計算基盤（部分実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity ファクター計算方針を実装するモジュールの骨組み。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針（関数 calc_momentum を含むがファイル末尾で切れているため一部未完）。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を定義。

### Changed
- n/a（初回リリースのため既存からの変更はありません）

### Fixed
- n/a（初回リリース）

### Notes / Important behavior
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データを本番 DB と分離したい場合は設定を確認してください。
- Execution は paper_trading 時に専用 DB を用いるため本番 DB とペーパートレードデータが混在しません。
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / cpu affinity の設定は権限に依存します。失敗した場合は警告が出力され、処理は続行されます。
- ロギングはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

今後の想定作業（例）
- research/factor_research.py の未完成部分の実装完了（factor 計算の SQL / 集計処理）。
- ExecutionEngine / SystemMonitor のユニットテスト充実化。
- 単体・統合テストの追加、CI ワークフロー整備。
- ドキュメント（API 仕様書、アーキテクチャ図、運用手順）の整備。

[0.1.0]: https://example.com/release/0.1.0
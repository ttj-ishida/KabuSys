# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（現時点のコミットに対する未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム KabuSys の基本機能を実装しました。

### Added
- 全体
  - パッケージ初期リリース。モジュール群（monitoring / execution / portfolio / utils / research / tools）を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全終了処理。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 SQLite（monitoring DB）と DuckDB を接続し、監視 DB の初期化を実行。
    - check_once() 実行時の例外を捕捉してログ出力し、ループ継続する耐障害性を確保。

  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を利用し、paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中は実行エンジンを別スレッドで起動し、stop フラグ検知で安全に停止。
    - pid ファイル（data/execution.pid）管理。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local、OS 環境変数保護）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env ファイルの堅牢なパーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu API / LINE / DB パス / しきい値 / 環境・ログ設定など）。
    - 環境変数の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を組み込み、無効値で明示的な例外を送出。

  - config_setup.py:
    - 対話式 .env ウィザードを追加。既存 .env の読み込み、項目別入力、シークレットマスク、保存確認を行う。

  - validate_config.py:
    - 起動前チェック用 CLI を実装。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時の追加ガード（LINE 通知設定や Kill Switch 設定）を行う。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告ログを出力。

  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャーを計算し上限を超えるセクターの候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull"/"neutral"/"bear" -> 1.0/0.7/0.3）。未知のレジームはフォールバックで 1.0 とし警告ログ。

  - portfolio/position_sizing.py:
    - ポジションサイズ計算（risk_based / equal / score）を実装。単元株（lot_size）で丸め、1銘柄上限・投下資金上限・コストバッファを考慮したスケーリング・配分ロジックを含む。
    - aggregate cap（合計投下額が利用可能現金を超える場合）でスケールダウンし、残余キャッシュで端数を lot 単位で割り当てる仕組みを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 全起動スクリプトで利用する統一ロギング設定を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。既存ハンドラは一度クリアしてから再設定。
    - LOG_DIR/LOG_LEVEL の解決順を明示。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py:
    - クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows/Linux/macOS に対応し、psutil の権限エラーや未対応 OS は安全にスキップして警告ログを出力。

- 解析・検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加。paper_trading SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシ）を集計し Pass/Fail を判定する CLI を実装。
    - CLI 引数で期間指定（--from/--to）と DB パス指定（--db）に対応。
    - P95 の計算、データ不足時の N/A 処理、閾値による判定ロジックを実装。

- 研究用モジュール（research）
  - research/factor_research.py:
    - ファクター計算用の骨格と定数を追加（モメンタム、MA、ATR、出来高系などの計算を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。

### Changed
- DB の取り扱い
  - run_monitoring.py は監視処理において環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する旨を明示（監視データは本番 DB を参照/更新）。
  - run_execution.py は paper_trading モード時に専用の paper_sqlite_path を使用することで本番データと完全に分離するように設計。

- 設定自動読み込み
  - .env の読み込みで OS 環境変数を保護する仕組みを導入（.env.local は上書き可能だが OS 環境変数は上書きされない）。

- ログ出力先
  - デフォルトで stdout を標準出力に使い、ファイル出力が不可能な場合はフォールバックでコンソールのみで継続するよう改善。

### Fixed
- 設定値パースの強化
  - MONITOR_POLL_INTERVAL の値が不正（0 以下や非整数）の場合に警告を出しデフォルト（60 秒）にフォールバックして起動を継続するように改善。

- 監視 DB 初期化の冪等性
  - run_execution.py 起動時にも init_monitoring_db を呼び出して監視テーブルの存在を保証（何度でも安全に呼べるように設計）。

### Security
- 今回のリリースで特記すべきセキュリティ修正はありません。ただし .env（シークレット値）を .git にコミットしないよう README 等で注意することを推奨します（config_setup.py の生成ヘッダにもその旨を記載済み）。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成しています。実際の運用上の変更履歴やリリースノートはリポジトリのコミット履歴やリリース手順に合わせて適宜更新してください。
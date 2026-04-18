# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは手元のソースコードから推測して作成した変更履歴です。

フォーマット:
- 変更は semantic なカテゴリ（Added / Changed / Fixed / Security / …）に分類しています。
- 各項目はコード内の実装・仕様から推測して記載しています。

<!--
参考: https://keepachangelog.com/ja/1.0.0/
-->

## [Unreleased]

- 開発中の変更はここに記載してください。

## [0.1.0] - 2026-04-18

### Added
- パッケージ初期リリースとして主要機能を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）およびモックブローカーを使用し、本番 DB と分離して動作。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトディレクトリ下の data/stop_requested.flag による。
  - 設定管理
    - config.py: 環境変数/.env ファイルの取り扱い、プロジェクトルート自動検出 (.git / pyproject.toml) 、Settings クラス（各種設定プロパティとバリデーション）を実装。
    - config_setup.py: 対話式ウィザードで .env を生成 / 更新する CLI。秘密項目はマスク表示、保存前の確認あり。
    - validate_config.py: 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）など。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 各銘柄の発注株数計算（calc_position_sizes）。risk_based / equal / score の allocation_method をサポートし、単元株（lot_size）丸め、aggregate cap によるスケールダウン処理を実装。
  - リサーチ
    - research.factor_research: DuckDB 接続を受けてファクター（モメンタム、ボラティリティ、Value など）を計算するための基礎実装（関数雛形および定数群を含む）。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し、閾値に基づく PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
  - ユーティリティ
    - utils.logging_setup: 統一的ロギング設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして fallback。
    - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を提供。アクセス権限がない場合は警告を出力して続行。
  - データベース初期化
    - monitoring.monitoring_db.init_monitoring_db を各スクリプト起動時に呼ぶことで、監視用テーブルの存在を保証（冪等）。
  - パッケージメタ
    - __init__.py にバージョン __version__ = "0.1.0" とエクスポート群を追加。

### Changed
- （初版のため該当なし：今後のリリースで変更点をここに追記）

### Fixed
- .env のパースロジック強化（config._parse_env_line）
  - export KEY=val 形式への対応。
  - シングル/ダブルクォート内でのバックスラッシュエスケープを考慮して値を抽出。
  - クォートがない場合のインラインコメント（#）の扱いを改善。
- 自動 .env ロードの安全化
  - OS 環境変数を保護する protected セットを導入し、.env や .env.local の上書き挙動を制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- ロギング設定の堅牢化
  - ログディレクトリ作成に失敗しても起動を継続し、コンソール出力のみでログを残すフォールバックを実装。
  - StreamHandler は stdout に出力して cron/Task Scheduler との相性を考慮。
- ExecutionEngine 起動の安全策
  - 起動時に停止フラグ（data/stop_requested.flag）が立っている場合は起動を中止。
  - スレッド停止はフラグ検知で engine.stop() を呼ぶことで安全に終了を試みる。
- Monitoring の安定化
  - check_once() 実行中に例外が発生してもループを停止せずログに例外を記録して次のポーリングまで継続。

### Security
- 必須機密情報（J-Quants トークン / kabu API パスワード）は Settings で必須扱いにし、未設定時に ValueError を発生させることで起動前に検出可能に。
- .env を生成する際に「絶対に Git にコミットしないこと」という注意文を .env ファイルヘッダに記載。

### Documentation
- 各モジュールに docstring と使用例を追加し、実行方法や環境変数の説明を明記。
  - run_execution.py / run_monitoring.py / config_setup.py / validate_config.py / tools.paper_verification_report.py などに使用方法コメントあり。
  - portfolio モジュールや position sizing の設計ノート（どのドキュメントのセクションに対応するか）を docstring に記載。

---

注記:
- 本 CHANGELOG は提供されたソースコードの構造・コメント・実装から推測して作成したものです。実際のリリースノートや履歴管理と差異がある可能性があります。必要であれば、特定ファイルの変更点（コミットハッシュや詳細な差分）に基づいて調整します。
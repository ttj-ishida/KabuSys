# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリースノートは慣例に従い以下のカテゴリで記載します: Added, Changed, Fixed, Deprecated, Removed, Security
- 日付はリリース日（YYYY-MM-DD）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20
初回公開リリース（コードベースの機能を推測してまとめたリリースノート）。

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジン実行を別スレッドで管理。
    - 停止用フラグファイル（data/stop_requested.flag）を監視し、検知時に安全に停止する仕組みを実装。実行中の PID ファイル管理に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルト 60 秒のポーリング間隔で監視を実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。不正値は警告を出しデフォルトへフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（設計上の意図を明示）。
    - ポーリング中の例外をキャッチして次回ポーリングまで待機する堅牢化。
- 設定・環境
  - config.py
    - Settings クラスを導入し、環境変数の取得・検証を一元化。J-Quants / kabuステーション / LINE / DB / 監視閾値 等のプロパティを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。.env/.env.local の読み込みルール（OS 環境変数優先、.env.local は上書き可）を実装。
    - .env の行パースを強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START など運用向けオプションを追加。
- 設定支援・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目はマスク表示、選択肢/デフォルトのサポート。
    - 既存 .env の読み込み・再利用機能、保存前の確認プロンプトを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な妥当性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML がない場合はスキップ）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。コンソール出力（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）に対応。ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX (Linux, macOS, FreeBSD) を吸収。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を追加。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py
    - 株数算出ロジック (calc_position_sizes) を実装。risk_based / equal / score の配分方式、単元株 (lot_size) での丸め、aggregate cap（投下総額のスケールダウン）、cost_buffer を考慮した安全弁を備える。
- 監査・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み取り、稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して検証レポートを出力する CLI を追加。
    - P95 計算、期間フィルタ（--from / --to）、DB パス解決（引数 > 環境変数 > デフォルト）を実装。閾値による PASS/FAIL 判定を行う（稼働率 99% 等の基準が設定済み）。
- データベース / 分析統合
  - DuckDB 接続を利用する設計が各所で採用（Execution/Monitoring で duckdb_path を設定して接続）。将来の分析ワークフローを見据えた設計。

### Changed
- ログ出力の設計方針を統一
  - すべての起動スクリプトは setup_logging を呼び出して一貫したログ管理を行うよう変更（ファイルローテーション・stdout 出力の統一）。
- .env 自動読み込みの振る舞い
  - OS 環境変数は保護され、.env/.env.local の上書きルールを明確化（.env.local は override=True）。

### Fixed
- 監視ループの堅牢化
  - SystemMonitor.check_once() 実行中の例外をキャッチしてループを継続するようにして、単一例外で監視が停止するのを防止。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 負値や非整数が設定された場合に警告を出してデフォルト値（60秒）にフォールバックするように修正。

### Deprecated
- なし

### Removed
- なし

### Security
- センシティブな設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_CHANNEL_ACCESS_TOKEN）を .env ウィザードでマスク表示し取り扱いを明記。
- .env を絶対にリポジトリへコミットしない旨をドキュメント化（config_setup の生成ヘッダに記載）。

---

注: 本 CHANGELOG は提供されたコードからの推測に基づいて作成したものであり、実際のプロジェクト履歴やリリース日・バージョニングはリポジトリの公式履歴に従ってください。
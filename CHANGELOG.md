# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルはコードベースの現状（src/ 以下の実装）から推測して作成した変更履歴です。

※ バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用のエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用の sqlite_path を使用する設計。

- 設定管理機能を追加
  - src/kabusys/config.py: Settings クラスを追加し、環境変数から設定値を取得するユーティリティを実装。
    - .env / .env.local の自動読み込み（プロジェクトルート検出）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可能。
    - .env パースにおいて export 形式、クォート文字列、エスケープ、行末コメントを考慮した堅牢な実装を導入。
    - 各種設定プロパティ（DB パス、PID / Kill flag パス、Paper Trading 関連設定、監視閾値、環境名チェック等）を提供。
    - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH（paper_sqlite_path）をサポート。

- 設定ユーティリティと CLI
  - config_setup.py: 対話式の .env 作成／更新ウィザードを追加（項目・デフォルト・シークレット入力・保存確認を提供）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL のバリデーション、DB パス親ディレクトリチェック、config/*.yaml 存在・パースチェック（PyYAML があれば内容検証）を実行。--strict オプションで警告を FAIL 扱いにできる。

- Paper Trading 向けの解析ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite データを集計して検証レポートを出力するスクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を計算。
    - 各種基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - コマンドラインで期間指定（--from / --to）や DB パス指定（--db）に対応。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 銘柄ごとの株数計算ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を使った保守的見積り等を実装。
  - portfolio パッケージのエクスポートを整備（__all__）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。
    - stdout 出力用 StreamHandler（stdout を使用）と、日次ローテート（TimedRotatingFileHandler）を組み合わせて設定。
    - 既存ハンドラの安全なクリーンアップ（重複防止）と、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを実装（Windows / POSIX 差異吸収）。CPU affinity 設定関数も提供（set_cpu_affinity）。psutil を利用し、権限や未対応 OS の場合は警告を出して安全にスキップ。

- リサーチ基盤（スケルトン）
  - research/factor_research.py: DuckDB を使ったファクター計算の雛形（モメンタム等の定数・関数の枠組み）を追加（実装は一部開始）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- ログ出力のデフォルト動作を明確化
  - logging_setup によって、ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）が統一された。
  - ログファイルはデフォルトで logs/<app_name>.log に日次ローテーションで出力（30 日保持）。
  - コンソール出力は stderr ではなく stdout を使用（cron 等でのリダイレクト考慮）。

- 設定ロードの優先順位
  - OS 環境変数 > .env.local > .env の優先順位で自動ロードされるようにした（プロジェクトルートが特定できる場合のみ）。.env.local は既存 OS 環境変数を保護して上書きする設計。

- Execution / Monitoring の DB 用法を明確化
  - monitoring は環境に関係なく本番用 sqlite_path を使う（監視データが常に一元化されるように設計）。
  - execution は paper_trading 環境時は paper_sqlite_path を使用して本番データと明確に分離。

- 停止制御
  - run_execution / run_monitoring で data/stop_requested.flag を監視して安全に停止するロジックを追加（起動時の既存フラグ検査・実行中のフラグ検知でエンジン停止）。

### Fixed
- .env パーサの堅牢化
  - export 構文、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。これにより .env の微妙な書式差分で発生する誤読を防止。

- 環境変数の不正値対処
  - MONITOR_POLL_INTERVAL の整数変換で不正な値（非数、0 以下）を検出した場合にデフォルトへフォールバックし、警告ログを出すようにした（run_monitoring）。

- ログハンドラ二重登録の回避
  - setup_logging() で既存ハンドラを flush/close のうえ削除してから再設定するようにし、複数回 setup_logging を呼んでも重複してログが出力されないようにした。

- 監視 DB 初期化の冪等化
  - init_monitoring_db(sqlite_conn) を Execution 起動時にも呼び、監視テーブルの存在を保証（複数回呼んでも安全）。

- process_priority の堅牢化
  - Windows / POSIX の差異に対して getattr フォールバックや例外キャッチを追加し、権限不足や未対応 OS でも安全にスキップするようにした。

### Notes / Known issues
- research/factor_research.py は計算ロジックの骨組みが実装されているが、実装途中（calc_momentum などの詳細が未完）な箇所があるため、本格利用前に追加実装・テストが必要。
- position_sizing 等のロジックには TODO コメントが残っており、将来的に銘柄ごとの lot_size マスタ対応や価格フォールバック（前日終値等）の改善が予定されている。
- Paper Trading 検証レポートは SQLite テーブル構造（system_status, trade_logs, risk_logs 等）に依存する。期待するスキーマが存在しない場合は N/A 表示や 0 件扱いになる。
- config_setup で生成される .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（ファイルヘッダでもその旨を明示）。

--- 

この CHANGELOG はコードベース（src/ 以下）の実装内容に基づいて推測して作成しています。実際のリリースノートや歴史的変更記録が別途存在する場合はそちらを優先してください。
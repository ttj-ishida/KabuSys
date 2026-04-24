# Changelog

すべての非破壊的変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベースの現在の状態から推測して作成した変更履歴です（推測に基づく注記あり）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 基本アプリケーション骨格を実装
  - モジュール群: portfolio, execution, monitoring, utils, config, research, tools を追加。
  - エントリポイントスクリプト:
    - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite を使用する（本番 DB と分離）。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 設定関連 CLI:
    - config_setup: 対話式ウィザードで .env を生成/更新するツールを追加。
    - validate_config: .env と config/*.yaml の事前検証ツールを追加（--strict フラグ対応）。
  - ツール:
    - paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加（期間指定・DB指定オプション対応）。

- ポートフォリオ構築ロジック（純粋関数）
  - select_candidates, calc_equal_weights, calc_score_weights を追加（スコア加重のスコア合計が 0 の場合は等金額配分にフォールバックし警告）。
  - apply_sector_cap, calc_regime_multiplier を追加（セクター集中上限の除外ロジック、レジームに応じた乗数）。
  - calc_position_sizes を追加（risk_based / equal / score の割り当て方式、lot_size/コストバッファ/aggregate cap の実装）。

- 設定管理
  - Settings クラスを実装し、環境変数から設定値を取得する API を提供（各種プロパティで型変換・検証を実施）。
  - .env 自動ロード実装: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動ロード。OS 環境変数は保護して上書きされない。

- ロギング & プロセス管理ユーティリティ
  - setup_logging: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を提供。権限不足や未対応 OS の場合は安全にスキップして警告を出力。

- Monitoring / Execution の DB 初期化
  - monitoring 用テーブルの初期化を行う init_monitoring_db を run_* スクリプト起動時に呼び出し、冪等に監視テーブル存在を保証。

- Paper Trading 検証レポート
  - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などの指標を集計して PASS/FAIL 判定を行うレポート生成機能を追加。
  - デフォルト閾値を定義 (稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms)。

### Changed
- 環境分離の方針を明確化
  - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する仕様（監視データの一元化意図）。
  - Execution は paper_trading 環境であれば paper_sqlite_path を使用し、paper_trading と本番 DB を分離。

- .env パーサの堅牢化
  - export プレフィックスのサポート、クォート文字のエスケープ処理、インラインコメントの取り扱いを実装。
  - 読み込み時に OS 側の環境変数を保護する protected 機能を実装（.env.local の上書き制御）。

- Logging 動作
  - ログ出力先として stdout を採用（cron 等で stdout/stderr を統合して扱いやすくするため）。
  - 既存ハンドラをクリアしてから再設定することで二重ログを回避。

### Fixed
- ポーリング間隔の耐障害性向上
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合にデフォルト（60 秒）へフォールバックして警告を出力する処理を追加。

- PAPER_FILL_MODE の検証
  - Paper Trading の fill モードに対する有効値検査を追加し、不正値時に明確なエラーを送出するように修正。

- calc_score_weights のフォールバック
  - 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告ログを出す動作を保証。

- calc_regime_multiplier の既定値フォールバック
  - 未知のレジームラベルに対して 1.0 でフォールバックし警告を出すように修正。

- 設定検証ロジックの改善
  - validate_config にて YAML パーサがない場合は YAML 検証をスキップし警告を出すように変更（環境依存での起動失敗回避）。
  - validate_config に `--strict` を追加し、警告を FAIL 扱いにできるようにした。

### Security
- .env 生成時の注意喚起を明記（.env を Git にコミットしないこと）。

## [0.1.0] - 2026-04-24

初回公開想定リリース（推定）。上記の主要機能を含む初版リリース相当。

### Added
- パッケージのバージョン定義: __version__ = "0.1.0"
- 基本的なトレードエンジン周辺インフラ（ExecutionEngine 組立、OrderManager、OrderRepository、RiskManager、Reconciler 等）の骨格を実装（ファクトリや設定による依存注入を想定）。
- DuckDB および SQLite を用いたデータ管理インフラを組み込み（duckdb_path, sqlite_path の設定）。
- 実運用で想定される各種設定値（閾値、ログレベル、PID/kill/flgs パス等）の Settings プロパティ実装。
- 対話式設定ウィザード (config_setup)、事前検証ツール (validate_config)、紙トレード検証レポート (paper_verification_report) の追加。
- ロギング・プロセス優先度ユーティリティの追加。

### Changed
- （初期リリースのため特記事項なし）

### Fixed
- （初期リリースのため特記事項なし）

---

注:
- 本 CHANGELOG は現行ソースコードの実装内容から機能追加・修正を推測して作成したものです。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、実コミットログ（git log）やリリース日時等を参照して正確な日付／変更点に差し替えてください。
# Changelog

すべての変更は Keep a Changelog の慣例に従って記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般:
- バージョニングはセマンティックバージョニングを想定しています。
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-21

### Added
- 初回公開リリース。日本株自動売買システム "KabuSys" の基本機能を実装。
- 起動スクリプト・デーモン機能
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内の `data/stop_requested.flag` を監視して実施。
    - 監視用 DB 初期化（SQLite）と DuckDB 接続を確立。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の MockBrokerClient と専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離。
    - 実行中プロセスは PID ファイルを出力し、停止フラグで安全に停止可能。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で engine.stop() を呼び出す仕組みを採用。

- 設定管理
  - config.py: Settings クラスを実装。
    - `.env` / `.env.local` の自動ロード（プロジェクトルートは `.git` または `pyproject.toml` で検出）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 様々な設定項目（DB パス、API トークン、環境種別、閾値等）をプロパティ経由で取得。値検証（列挙値チェック等）を実装。
    - `.env` パース機能はシングル/ダブルクォート、エスケープ、`export KEY=val` 形式、インラインコメントなどに対応。
  - settings インスタンスをモジュールレベルで提供。

- CLI ツール
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）を検証。
    - `--strict` オプションで警告も失敗（exit 1）扱いにできる。
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新する機能を追加。
    - シークレット項目のマスク表示、既存値の取り込み、説明文を付与。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`。期間フィルタ対応（--from / --to）。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio/portfolio_builder.py:
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
  - portfolio/position_sizing.py:
    - calc_position_sizes を実装。`risk_based`, `equal`, `score` の配分方式をサポートし、単元株（lot_size）丸め・aggregate cap（利用可能現金）でのスケール調整ロジックを実装。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに基づく乗数）を実装。

- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定するユーティリティを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。
  - utils/process_priority.py:
    - set_process_priority（Windows/Linux/macOS に対応した優先度設定）と set_cpu_affinity（最初の N コアに固定）を追加。
    - 実行環境で権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- DB / 分析基盤
  - DuckDB 接続を想定したコードを導入（duckdb ライブラリ依存）。
  - 監視用の SQLite テーブル初期化関数（monitoring.monitoring_db.init_monitoring_db）を使用する仕組みを導入（冪等）。

- 研究用モジュール（初期実装）
  - research/factor_research.py にモメンタム等のファクター計算の骨子を実装（DuckDB の prices_daily テーブル参照、各種窓や定数定義を含む）。一部実装は継続作業が必要。

### Changed
- ログ出力
  - デフォルトで StreamHandler は stdout を使用（cron/Task Scheduler などで stderr/stdout をまとめて扱う運用を考慮）。
- run_monitoring.py
  - `MONITOR_POLL_INTERVAL` の不正値（整数変換失敗や 0 以下）を検出してデフォルトにフォールバックし、警告ログを出力するようにした。
- run_execution.py
  - Paper Trading 時は専用 SQLite を使用して本番 DB と分離する仕様を明確化。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善し、実運用での `.env` 設定の柔軟性を向上。

### Known issues / Notes
- research/factor_research.py の calc_momentum 関数以降の実装が途中で終わっている箇所があり、ファクター計算の完全実装は今後の作業となります。
- portfolio/risk_adjustment.apply_sector_cap:
  - 価格データが欠損（price = 0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討。
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size をサポートする拡張予定（現在は全銘柄共通 lot_size を想定）。
- validate_config.py の YAML 検証は PyYAML が未インストールの場合はスキップし、その旨を警告します。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでの例外をログに落としてスキップする実装（安全にフォールバック）。

### Dependencies / Requirements
- 実行には外部ライブラリ（例: duckdb、psutil）が必要な箇所があります。ツールによっては PyYAML があると追加の検証を行います。
- デフォルトの DB/ログパス等はプロジェクト相対の `data/` / `logs/` を利用します。環境によっては `.env` でパスを上書きしてください。

---

今後の予定（例）
- research/factor_research の完実装と単体テスト追加
- portfolio モジュールの単体テスト作成（position sizing のスケーリングや端数処理の網羅）
- ExecutionEngine / BrokerClient のインターフェースと PaperTrading のシミュレーション精度向上
- ドキュメント（設計書・運用手順）の整備

（この CHANGELOG はリポジトリ内のコードから推測して作成しています。実際のコミット履歴とは対応していない場合があります。）
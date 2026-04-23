# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、プロジェクトのリリース履歴と主要な変更点を日本語でまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョン定義を追加。
- 環境設定・管理機能を追加
  - .env 自動読み込み機構（プロジェクトルート検索: .git / pyproject.toml 基準）。
  - 高度な .env パーサ：クォート内のエスケープやインラインコメント処理に対応（src/kabusys/config.py）。
  - Settings クラスを実装し、環境変数から各種設定を取得・検証（DB パス、ログレベル、Paper Trading 等）。
- 対話式設定ウィザードを追加（.env 作成/更新支援）
  - src/kabusys/config_setup.py: 複数設定項目の対話入力、既存 .env の読み込み、保存機能。
- 設定検証 CLI を追加
  - src/kabusys/validate_config.py: 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス・config/*.yaml 存在チェック、production 向け注意喚起等。--strict オプションをサポート。
- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py:
    - プロセス優先度を高に設定してから起動。
    - Paper Trading 環境では専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理、PID ファイル管理。
- 監視ループ起動スクリプトを追加
  - src/kabusys/run_monitoring.py:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - check_once() の例外を捕捉してログ出力し次回ポーリングに継続。
- ロギング・プロセス制御ユーティリティを追加
  - src/kabusys/utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - src/kabusys/utils/process_priority.py:
    - Windows / POSIX（Linux, Darwin, FreeBSD）向けにプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity 設定関数も追加（利用可能なコア数と整合する安全実装）。
    - 権限不足や未対応環境では警告ログを出してスキップ。
- ポートフォリオ構築モジュールを追加（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - 候補選出（スコア降順）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（売却予定銘柄の除外や unknown セクターの扱い）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear を実装、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py:
    - 発注株数決定ロジック calc_position_sizes（allocation_method: risk_based / equal / score、lot_size、cost_buffer、aggregate cap のスケーリングと端数配分ロジックを実装）。
  - パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- リサーチ（ファクター計算）骨子を追加
  - src/kabusys/research/factor_research.py（モメンタム・ボラティリティ・流動性・Value 指標の計算方針、DuckDB 接続利用、P95 等のユーティリティを含む。実装は途中で切れているが設計方針と定数を含む）。
- Paper Trading 検証レポート生成スクリプトを追加
  - src/kabusys/tools/paper_verification_report.py:
    - SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、P95 レイテンシなどを集計してレポート出力。
    - 判定基準（閾値）を定義し PASS/FAIL を判定。
    - 日付フィルタ、欠損時の安全ハンドリング（OperationalError を捕捉）を実装。
- monitoring 用 DB 初期化呼び出しを統一的に行うための参照を追加（init_monitoring_db の呼び出し箇所を run_* に追加）。

### Changed
- 環境変数の読み込み優先順を明確化
  - OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
- ログ出力先は標準出力（stdout）をデフォルトで使用する方針に変更（cron / scheduler での取り扱い配慮）。
- run_monitoring: 環境に依存せず監視 DB 初期化に本番 sqlite_path を使用する設計に変更（監視データは本番 DB に集約）。
- run_execution: Paper Trading 時は settings.is_paper フラグに基づき専用 DB に切り替えることで本番 DB と分離。
- position_sizing の aggregate cap スケーリングの実装を導入（コストバッファ、lot_size 単位での再分配など）。端数の扱いは安定性を重視して deterministic（再現可能）に実装。
- .env パーサは export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善（より多くの .env フォーマットに耐性を持たせた）。

### Fixed
- run_monitoring: MONITOR_POLL_INTERVAL が 0 以下や非整数の場合に time.sleep に渡して ValueError になる問題を回避し、無効値時はデフォルト（60 秒）にフォールバックして警告を出す。
- 複数モジュールでの DB 接続後の例外時にリソースが適切にクローズされない可能性を改善（finally で接続を close）。
- logging_setup: ログディレクトリ作成失敗時にハンドラ設定が壊れる問題を回避し、ファイルハンドラ作成に失敗した際はコンソールのみで継続。
- process_priority: 未対応 OS や権限不足時にこけるのを防ぎ、警告ログでフォールバックするよう改善。

### Security
- .env の初期テンプレートや config_setup の注意書きに「.env を絶対に Git にコミットしないこと」を明記（src/kabusys/config_setup.py の出力ヘッダ）。

---

注:
- この CHANGELOG は現在のコードベース（提供されたソースファイル群）から推測して作成しています。実際の変更履歴（コミット履歴やリリースノート）に基づく正確な履歴とは異なる場合があります。必要であれば、git のコミットログに基づいた正式な CHANGELOG 生成をお手伝いします。
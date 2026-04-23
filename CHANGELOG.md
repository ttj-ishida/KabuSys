# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。
[https://keepachangelog.com/ja/1.0.0/]

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-23

初回公開リリース。システム全体のコア機能を実装しました（設定管理、起動スクリプト、監視、実行エンジン周辺、ポートフォリオ構築、ユーティリティ、検証/設定ウィザード、レポートツール等）。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
- 設定・環境管理
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
    - J-Quants、kabuステーション、LINE、DBパス、各種閾値、実行環境フラグ（KABUSYS_ENV）等をプロパティで取得可能。
    - .env 自動読み込み機能を実装（プロジェクトルート検出、.env / .env.local の読み込み順序）。
    - .env パーサの実装: export 構文、クォート文字列、インラインコメント、エスケープを考慮して安全にパース。
    - 必須値未設定時に明示的なエラーを投げる _require() を提供。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を生成／更新できるウィザード（項目一覧、既存値の再利用、シークレット入力、保存の確認など）。
    - .env のテンプレート生成と書き込み機能を実装（Git にコミットしないことを明記）。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在・パースチェックを行う。
    - --strict オプションで警告も失敗扱いにできる。
- 実行 / 監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度設定、SQLite / DuckDB 接続、paper_trading 時の DB 分離（PAPER_TRADING_SQLITE_PATH を利用）をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組立て、ExecutionEngine の起動・停止制御（停止フラグ監視）を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。デフォルト 60 秒。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop_requested.flag による優雅な停止をサポート。
- 監視 DB 初期化
  - init_monitoring_db 呼び出しを起動時に行い、監視用テーブルが存在することを保証（冪等）。
- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights（スコア全部 0 の場合はフォールバック）を実装。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有を考慮したセクター上限フィルタ（"unknown" セクターは無視）。
    - calc_regime_multiplier：market レジームに応じた投下資金乗数（bull/neutral/bear）とフォールバック挙動。
  - 発注株数計算（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式に対応。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、コストバッファ考慮の実装。
    - 余り配分ロジック（fractional remainder）で再現性を保ちながら lot_size 単位で追加配分。
- 研究用ファクター計算（骨組み）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR / ボリューム等の指標を計算する方針と定義を含む（関数 calc_momentum の雛形＋定数）。
- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）をルートロガーへ一括設定するユーティリティ。
    - LOG_DIR/LOG_LEVEL の解決順、既存ハンドラの安全な再設定（flush/close → remove）を実装。ログディレクトリ作成失敗時のフォールバックも考慮。
  - プロセス優先度と CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して set_process_priority, set_cpu_affinity を提供。権限不足等の失敗時は警告ログでスキップ。
- ツール
  - Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from, --to）と DB パス（--db / 環境変数）をサポート。
- モジュールエクスポート
  - package のポートフォリオ API を __init__ で整理して再エクスポート（select_candidates 等をトップレベルで利用可能に）。

### Changed
- 設計関連（ドキュメント的記載）
  - 各モジュールの docstring やコメントで設計方針（DB 分離、純粋関数、例外処理、フォールバック）を明示化。
  - ロギングは stdout を標準出力に出す方針に統一（cron / Task Scheduler を考慮）。

### Fixed
- 環境読み込みの堅牢化
  - .env の読み込みで OS 環境変数を保護する仕組みを導入（.env の上書き時に protected set を参照）。
  - .env パースの厳密化によりクォーテーションやエスケープ、インラインコメントの扱いを改善。
- ポジション計算の数値安定性
  - position_sizing の aggregate スケーリング処理で残余キャッシュを考慮した端数配分ロジックを実装して発注量の過積載を抑制。

### Deprecated
- なし

### Removed
- なし

### Security
- .env ファイルは絶対に Git にコミットしない旨を設定ウィザードとテンプレートに明記。
- 環境変数の必須値が未設定の場合は起動前に検証ツールで検出できるようにし、安全な運用を支援。

---

注記:
- 実際の変更点はソースコードのスナップショットから推測して記載しています。リリースノートとして用いる際は実際のコミット履歴・差分と照合してください。
- 今後のリリースでは breaking changes / migration notes を明記してください。
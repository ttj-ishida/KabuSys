CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- リリース済みの最初の安定版として 0.1.0 を作成しました（下記参照）。

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行・監視用の起動スクリプトを追加
    - run_execution.py: ExecutionEngine を起動するエントリポイント（スレッドで実行、停止フラグ監視、PID ファイル管理）。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（停止フラグ検知、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、監視は常に本番 sqlite_path を使用）。
  - 環境設定支援・検証ツール
    - config_setup.py: 対話式 .env ウィザード（.env の初期作成/更新を支援）。
    - validate_config.py: 起動前の設定検証 CLI（必須環境変数・ファイルパス・YAML の構文・本番向けガード等のチェック、--strict オプション）。
  - Paper Trading 用検証レポートツール
    - tools/paper_verification_report.py: ペーパートレード SQLite を解析して稼働率・注文成功率・レイテンシなどを集計・判定（P95 計算・閾値による PASS/FAIL 出力）。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、コストバッファ対応。
  - 研究用ファクター計算基盤（開始）
    - research/factor_research.py: モメンタム等のファクター計算ロジックの骨組み（DuckDB 接続で prices_daily/raw_financials を参照する設計）。
  - ユーティリティ
    - config.py: 環境変数の取り扱いと Settings クラスを追加。.env の自動ロード（.env / .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD の扱い）、高度な .env パース（export 形式、クォートとエスケープ、インラインコメント処理など）。
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティ（コンソール stdout と日次ローテーションファイル出力、ログディレクトリ作成失敗時のフォールバック）。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX の差分吸収、例外を安全にハンドル）。
    - monitoring.monitoring_db.init_monitoring_db の呼び出しを run スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - パッケージ情報
    - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- ロギングの振る舞い
  - StreamHandler を stderr ではなく stdout に向ける設計に変更（Task Scheduler/cron 等とリダイレクトを考慮）。
  - 既存ハンドラがあれば一度 flush/close してから再設定し、二重設定を防止。
- .env 読み込みの優先順位と保護処理を明示
  - OS 環境変数を保護する protected セットを用意し、.env.local が .env を上書きする挙動を実装。
- 実行/監視起動時のプロセス優先度を "high" に設定する呼び出しを標準化（set_process_priority を最初に呼ぶ）。

Fixed
- .env パースの堅牢化
  - export KEY=val 形式のサポート、シングル/ダブルクォートでの値のエスケープ処理、インラインコメントの扱い等を実装し、誤ったパースによる設定ミスを軽減。
- run_monitoring のポーリング間隔設定のバリデーション
  - MONITOR_POLL_INTERVAL が不正値（0 以下や非整数）の場合、ログ警告を出してデフォルトにフォールバックするように修正（time.sleep に渡す ValueError を予防）。
- ログディレクトリの作成失敗時にファイルハンドラをスキップしてコンソールログのみで継続するフォールバックを実装。
- process_priority / set_cpu_affinity が権限不足や未サポート環境で例外を投げないように警告ログで安全にスキップ。

Security
- .env の取り扱いに関する注意書きを config_setup のテンプレートに追加（.env を Git にコミットしない旨を明記）。

Notes / Implementation details
- ExecutionEngine/RiskManager/OrderManager 等の主要コンポーネントは実装済みのインターフェースで組み立てられ、Execution 起動スクリプトは BrokerClientFactory 経由で本番/モックブローカーを切り替え可能。
- Paper Trading 用 DB と本番 DB は明確に分離（paper_trading モードでは PAPER_TRADING_SQLITE_PATH を使用）。
- portfolio/position_sizing の allocation ロジックは lot_size（単元株）に基づく丸め、available_cash に対する aggregate スケーリング、cost_buffer による保守的見積りを採用。
- tools/paper_verification_report は複数テーブル（system_status, trade_logs, risk_logs）を参照し、P95 レイテンシなどの指標を計算して閾値判定する。DB が存在しない/テーブルが無い場合も安全に N/A を出力。

Upcoming / TODO
- research/factor_research.py の実装完了（ファクタ計算関数の詳細実装の継続）。
- 銘柄別の lot_size を銘柄マスタでサポートする拡張（position_sizing の TODO）。
- monitoring・execution のユニットテスト強化（環境依存部分のモック化）。
- logging のさらなるメトリクス出力（構造化ログ等の検討）。

参照
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 日付は本 CHANGELOG の作成日: 2026-04-23

---

翻訳や項目の追加・修正が必要であれば指示してください。コード差分ベースではなく現状の実装内容から推測した CHANGELOG です。
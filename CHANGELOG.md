# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
追加・変更・修正の概要をリポジトリから推測して日本語でまとめています。

## [0.1.0] - 2026-04-21

### Added
- 初期リリース。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - エンジンスレッドをデーモンで起動し、data/stop_requested.flag の監視で安全に停止可能。
    - プロセス PID を data/execution.pid に記録する処理への対応（pid_file の注入）。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に依らず本番用の sqlite_path を使用して監視情報を保存。
    - data/stop_requested.flag による終了、KeyboardInterrupt での終了をハンドリング。
- 設定管理
  - config.py: Settings クラスを実装。環境変数から各種設定（API トークン、DB パス、監視閾値、ログレベル等）を取得・検証。
    - .env 自動ロード機能（プロジェクトルート検出に基づく）。優先順位: OS 環境 > .env.local > .env。
    - .env パースの強化（export 句対応、シングル/ダブルクォートとエスケープ、インラインコメント処理）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）。
    - is_live / is_paper / is_dev の便宜プロパティを追加。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env の読み込み・編集をサポートし、保存フォーマットを標準化。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければ警告）。
    - --strict モードで警告を失敗扱いにできるオプションを提供。
- ポートフォリオ構成
  - portfolio/portfolio_builder.py: 候補選定・等配分・スコア重み配分を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中抑制とレジーム乗数を実装（apply_sector_cap, calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数算出ロジックを追加（risk_based / equal / score の配分方式、単元株丸め、aggregate cap のスケーリング処理、コストバッファ考慮）。
  - portfolio パッケージを公開インターフェイスでまとめてエクスポート。
- 解析・研究
  - research/factor_research.py: DuckDB 接続を受けてファクター（モメンタム等）を計算するモジュールの骨格を追加（prices_daily / raw_financials 参照を想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - 日付レンジ指定（--from / --to）や DB パス指定（--db / 環境変数）をサポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を追加。
    - stdout へ出力する StreamHandler と、日次ローテート（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log）を組み合わせる。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、console のみで継続。
    - LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度と CPU affinity 設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - psutil の権限不足や未対応 OS を考慮してフォールバック・警告を出す設計。

### Changed
- ログ振る舞いの標準化:
  - すべての起動スクリプトは setup_logging を呼び出して一貫した出力フォーマットとファイルローテーションを利用するように統一。
- プロセス優先度の設定を起動直後に行うように全スクリプトで統一（パフォーマンス重視の初期設定）。

### Fixed
- .env のパース仕様を改善し、クォートやエスケープ、コメント処理の不具合を回避できるように実装（テキスト中の引用符やバックスラッシュエスケープに対応）。
- DB 初期化呼び出し（init_monitoring_db）を実行前に確実に行うことで、監視・実行処理でのテーブル未作成によるエラーを抑制（冪等な初期化）。

### Notes
- 一部のコンポーネント（ExecutionEngine、SystemMonitor、BrokerClientFactory、OrderManager など）は起動スクリプトから参照される実装の存在を前提としている。CHANGELOG はリポジトリから推測できる公開 API と起動フローを中心に記載しています。
- 本リリースではセキュリティ面（シークレットの扱い）は .env に依存しており、.env を絶対にコミットしない旨を config_setup の出力でも明記しています。運用時は適切なシークレット管理を推奨します。

---
今後のリリースでは、テストカバレッジ、エラーハンドリング強化、設定のより詳細な検証、および銘柄毎の lot_size を持つ拡張（position sizing の TODO）などを予定しています。
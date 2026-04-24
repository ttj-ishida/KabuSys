# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記録します。リリース履歴は API や実行フローの変更点を把握するための参考にしてください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-24
初版リリース。KabuSys のコア機能と運用用ユーティリティをまとめた最初の公開バージョンです。

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py に定義）。
- 設定管理
  - Settings クラス（src/kabusys/config.py）:
    - .env の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）等）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / KILL_FLAG_CLEAR_ON_START 等の環境変数を扱う。
  - .env パーサ実装: export 形式、クォート内エスケープ、インラインコメント取り扱いに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
- 実行・監視用起動スクリプト
  - run_execution（src/kabusys/run_execution.py）:
    - ExecutionEngine 起動ラッパー。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し、本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）。
    - スレッドで engine.run_session を実行し、フラグ検知で安全停止。
  - run_monitoring（src/kabusys/run_monitoring.py）:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了。
- CLI 管理ツール
  - config_setup（src/kabusys/config_setup.py）:
    - 対話式ウィザードで .env を作成/更新するツール。
    - 必須/任意項目のプロンプト、シークレットマスク、確認後に .env を書き出す。
  - validate_config（src/kabusys/validate_config.py）:
    - 起動前設定検証ツール（必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在/パース等）。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML が無ければ YAML 検証をスキップして警告を出す。
- ロギング / プロセス制御ユーティリティ
  - setup_logging（src/kabusys/utils/logging_setup.py）:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保存）を設定。
    - ログレベル/ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）。
    - ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - process_priority（src/kabusys/utils/process_priority.py）:
    - set_process_priority / set_cpu_affinity を提供。Windows/Linux/macOS の差分を吸収。
    - psutil による優先度／CPU affinity 設定（権限不足や未対応環境では警告ログ出力してフォールバック）。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates（スコア降順 + tie-break）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等金額フォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap（既存保有比率に基づくセクター上限フィルタ；unknown セクターは除外対象外）。
    - calc_regime_multiplier（market regime に基づく投下資金乗数、未知レジームはフォールバック警告）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）:
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、max_position/max_utilization, cost_buffer による保守見積り、アグリゲートスケールダウン処理を実装）。
- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）:
    - Paper Trading の SQLite DB を解析して稼働率 / 注文成功率 / 送信率 / レイテンシ（P95 等）を算出し、PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to)、--db オプション対応。デフォルト DB は data/paper_trading.db。
    - しきい値定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms 等）を実装。
- DuckDB を分析用途に利用する構成（duckdb_path 設定）を追加。
- monitoring DB 初期化ユーティリティの呼び出し（init_monitoring_db）を実行開始時に行うことでテーブル存在を保証。
- Research モジュールの骨組み（src/kabusys/research/factor_research.py）を追加（モメンタム等のファクター計算を想定、DuckDB を利用）。一部実装は継続作業。

### Changed
- なし（初版につき既存リリースからの変更なし）。

### Fixed
- なし（初版につき既知のバグ修正履歴なし）。

### Security
- なし（初版）。

### Notes / 運用メモ
- Paper Trading と Live は DB を分離（settings.paper_sqlite_path）。実際の発注は KABUSYS_ENV に応じて切り替えられるため、本番・検証環境を分離して運用可能。
- run_* スクリプトは stop flag（data/stop_requested.flag）を監視して安全に終了する機構を持つ。運用上の停止はこのフラグを立てるか、プロセスに SIGINT を送る。
- .env ファイルは絶対に Git にコミットしないこと（config_setup のヘッダにも注意書きあり）。
- ログはデフォルトで logs/<app_name>.log に出力され、日次ローテーション（30日保持）する。ログディレクトリ作成に失敗した場合はコンソールのみ出力になる。
- 一部モジュール（research 等）は今後の実装・拡張が予定されている。API の安定化に伴い minor リリースで追加していく予定。

## 既知の制限 / 今後の改善候補
- position_sizing: 銘柄ごとの lot_size を将来的に銘柄マスタから取得する設計に拡張予定（現在は全銘柄共通の lot_size）。
- apply_sector_cap: price_map に欠損（0.0）があるとエクスポージャが過少認識される可能性があり、フォールバック価格（前日終値等）導入を検討。
- factor_research モジュールは一部未完成（コメントで記載の通り）。DuckDB を活用した完全実装を継続する。
- process_priority / CPU affinity の設定は権限や環境依存で失敗する可能性があるため、運用環境でのドキュメント整備が必要。

---

（必要であれば、各機能ごとの詳細な変更点や設計意図、API 使用例を追記できます。どの部分を優先して詳細化しますか？）
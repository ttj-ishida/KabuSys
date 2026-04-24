# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-24

### Added
- 基本機能の初期実装（初回リリース）。
- 起動スクリプト / 運用ユーティリティ
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント切替をサポート（実運用・モックの透過的切替）。
    - 実行中の停止フラグ（data/stop_requested.flag）検知とエンジンの安全停止、PID ファイルの利用を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は KABUSYS_ENV に依らず本番向け sqlite_path を使用する設計に明示。
    - 停止フラグ検知でループを終了。KeyboardInterrupt による終了処理を明示。
- 設定管理・検証・セットアップ
  - config.py
    - 環境変数/`.env` 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env のパース（export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント処理）を実装。
    - Settings クラスに各種設定プロパティを実装（DB パス、KABU_API_BASE_URL、PAPER_FILL_MODE の検証等）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレットは表示マスク、保存前の確認プロンプトを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未導入時は YAML 検証をスキップする実装（警告出力）。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全スクリプトで共通利用可能なログ設定ユーティリティを追加。
    - stdout に StreamHandler を出力する（cron 等で stdout/stderr を一括リダイレクトしやすくするため）。
    - TimedRotatingFileHandler による日次ローテーションを実装（デフォルト logs/<app>.log、30日保持）。ログディレクトリ作成失敗時のフォールバック動作あり。
  - utils/process_priority.py
    - cross-platform（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - psutil を利用し、権限不足等が発生した場合は安全にスキップして警告出力。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコアソート）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターの扱い、レジームフォールバック動作を明記。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock および aggregate cap、コストバッファ（cost_buffer）を考慮したスケーリングと端数配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定（閾値はソース内で定義）を行う。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。
- リサーチ（ファクター計算）基盤
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム・Value・Volatility・Liquidity の計画、DuckDB を使った計算方針）。
    - calc_momentum の宣言と定数群が導入（実装継続中）。

### Changed
- パッケージ初版のため特記事項なし。

### Fixed
- 環境変数パースの堅牢化
  - export プレフィックス対応、クォート内部のバックスラッシュエスケープ、インラインコメント処理等を実装して .env の互換性を改善。
- MONITOR_POLL_INTERVAL の入力検証を追加
  - 0 や負数、非数の値を指定した場合に警告を出してデフォルト（60 秒）にフォールバックするようにした（time.sleep に無効な値を渡さないように保護）。
- ログ設定のフォールバック動作強化
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でもコンソール出力のみで継続するように修正（運用環境での起動失敗を回避）。
- プロセス優先度設定での例外処理追加
  - 権限不足や未サポート OS 時に例外が発生しても警告を出してスキップするようにした。

### Security
- 設定ウィザードでシークレット項目（API トークン等）はマスク表示。`.env` に関して「絶対に Git にコミットしないこと」を README コメントにて明示。

---

注記:
- This project は初版リリース（0.1.0）です。ドキュメントやユニットテスト、research モジュールの一部処理（calc_momentum の完全実装など）は継続的に整備予定です。
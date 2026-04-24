CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。互換性のあるバージョニングに従います。

[0.1.0] - 2026-04-24
-------------------

Added
- 初期リリース: KabuSys の基本的な自動売買/監視ユーティリティを実装。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。実行中は PID ファイル管理と停止フラグ検出を行い、スレッドでエンジンを実行・停止できる。
  - run_monitoring.py: SystemMonitor のポーリングループ実行スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用して監視データの一元化を図る。
- 設定周り:
  - config.py: 環境変数ラッパー Settings を実装。自動 .env 読み込み（.env / .env.local、OS 環境変数の保護ルールあり）、各種パス・フラグ・閾値や paper_trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレット入力、デフォルト値、選択肢をサポートし .env 保存テンプレートを出力。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在・本番時のガードチェックを行い、errors/warnings/infos を整形して返す。--strict オプションをサポート。
- ログ/プロセス管理ユーティリティ:
  - utils/logging_setup.py: ルートロガーの統一設定関数 setup_logging を追加。stdout StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: psutil ベースでプラットフォーム差分（Windows / POSIX）を吸収するプロセス優先度調整関数 set_process_priority と CPU affinity 設定関数 set_cpu_affinity を追加。アクセス権限不足時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py: シグナル選抜（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position と aggregate のキャップ、コストバッファを考慮したスケーリング処理を含む。
- 解析/レポート:
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加。システム稼働率、注文成功率（Fill/Send）、リスク却下数、API レイテンシ（avg/max/P95）を計算して PASS/FAIL 判定を行う。P95 の計算ロジックと閾値を定義。
- データベース:
  - DuckDB を分析用に使用（duckdb_path 設定）。run_execution/run_monitoring で DuckDB 接続を受け渡す設計を採用。
  - 監視用 SQLite の初期化を行う init_monitoring_db 呼び出しを組み込んで冪等性を確保。
- パッケージ情報:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- .env 自動読み込みの挙動を明確化:
  - プロジェクトルートは .git または pyproject.toml を基準に探索して決定。見つからない場合は自動ロードをスキップ。
  - .env の読み込みは OS 環境変数を保護（.env.local は上書き可能だが OS 環境変数は優先）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テストや CI 向け）。
- .env パーサーを堅牢化:
  - export プレフィックス対応、クォート処理（シングル/ダブル、バックスラッシュエスケープ）、インラインコメント処理、無効行スキップを実装。
- ログの標準出力先を stdout に統一:
  - StreamHandler を stdout に設定。cron/タスクランナーでの出力リダイレクト運用を想定。

Fixed
- 複数箇所でのリソースクローズ保証:
  - run_monitoring/run_execution で finally ブロックにて sqlite/duckdb 接続をクローズするように整理。
- 監視 / 実行の停止ロジック:
  - data/stop_requested.flag を用いた外部停止フラグの検出を追加。既に停止フラグがある場合は実行を開始しない（エンジン起動時の早期終了）。

Security
- .env に関する注意を documentation と config_setup のテンプレートに明記: .env を Git にコミットしないことを強調。
- シークレットな設定は config_setup の対話でマスク表示し、書き込み時も平文だがユーザーに確認の上保存する。

Known limitations / Notes
- research/factor_research.py はモメンタム等のファクター計算モジュールを実装中（calc_momentum の先頭実装が含まれる）が、ファイル末尾が途中で切れている（未完成の可能性あり）。実装完了・テストが必要。
- 一部 TODO が残る（例: price のフォールバックや銘柄別 lot_size の拡張など）。ログや警告で将来の改善点を注記している。
- process_priority の優先度設定や CPU affinity は権限に依存するため、設定に失敗した場合は警告ログを出し安全にスキップする設計。

Deprecated
- なし

Removed
- なし

Unreleased
- なし（本 CHANGELOG は初期 0.1.0 の状態を記述しています）

---

この CHANGELOG はソースコードの実装から推測して作成しています。実際の変更履歴やリリースノートに合わせて適宜調整してください。
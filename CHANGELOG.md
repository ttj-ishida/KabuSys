CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
このプロジェクトのバージョニングは SemVer を想定します。

Unreleased
----------
- 今後の変更履歴をここに記載します。

0.1.0 - 2026-04-22
-----------------
初回リリース。コードベースから推測される主要な追加機能・仕様は以下のとおりです。

追加 (Added)
- 実行・監視用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照する仕様。

- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 関連など）を扱う。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI。--strict オプションで警告も失敗扱いにできる。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML のパースチェック（PyYAML があれば）および本番向けガードチェックを実行。

- 設定読み込み・管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で判定）。.env/.env.local の読み込み順をサポートし、OS 環境変数の保護（上書き禁止）に対応。環境変数のパースはクォートやエスケープ、インラインコメントなどを考慮した実装。
  - Settings クラスで各種設定（パス、閾値、環境種別判定、PAPER_FILL_MODE の妥当性検証など）をプロパティとして提供。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークで選出。
    - calc_equal_weights, calc_score_weights: 等分配・スコア加重（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャが上限を超える場合、新規候補をフィルタリング（"unknown" セクターは対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出。単元株丸め（lot_size）、per-position と aggregate の上限制御、cost_buffer を考慮したスケーリングや端数処理を実装。

- 監視/実行に必要な共通ユーティリティ
  - utils/logging_setup.py: 一元的なログ設定関数 setup_logging を提供。stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップ。ログ保管日数は 30 日。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ（psutil を使用）。Windows/Linux/macOS (POSIX) の差を吸収し、権限不足・未対応環境では警告を出してスキップ。

- 監視データベース初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）を読み、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポートを出力。複数の閾値を用いた PASS/FAIL 判定を実施。P95 算出ロジック・期間フィルタ（ISO8601 UTC フォーマット）を実装。

- 研究用ファクター計算（開始）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算方針を実装（DuckDB 経由で prices_daily / raw_financials を参照）。calc_momentum などの関数に着手（ファイル末尾に未完の痕跡あり）。

仕様（Notes / Behavior）
- 監視は常に settings.sqlite_path を使用（KABUSYS_ENV に依らず本番 sqlite を参照するという設計決定）。
- 実行エンジンは KABUSYS_ENV=paper_trading の場合、専用の paper_sqlite_path を使用して本番とデータ分離。
- run_execution は起動前に data/stop_requested.flag が存在すれば起動せず終了する。稼働中は同フラグの検知で安全に停止する。
- run_monitoring は data/stop_requested.flag の存在でポーリングループを終了する。MONITOR_POLL_INTERVAL（秒）でポーリング間隔を制御。無効値はデフォルトにフォールバックして警告を出す。
- config の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化できる（テスト用途想定）。
- .env の読み込みは OS 環境変数を保護（既存キーは上書きしない）、.env.local は .env より優先して上書きする。
- logging_setup では stdout に出力するため、cron や外部ジョブランナーで stdout/stderr をリダイレクトする運用に配慮。

修正 (Fixed)
- 初期リリースのため明示的な「修正」は該当なし（今後のリリースで追記予定）。

既知の制約・ TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討する。
- portfolio/position_sizing.calc_position_sizes: 将来的には銘柄ごとの lot_size を導入する想定（現状は全銘柄共通の lot_size を使用）。stocks マスタの導入が想定されている。
- research/factor_research.py の末尾が未完（start_da... で切れている）。ファクター計算の一部実装が継続中である可能性がある。
- 一部の外部依存（psutil, duckdb, PyYAML 等）が存在し、環境により機能制限や警告を出す実装になっている（インストール状況に依存）。

内部・実装ノート
- ログ回転は日次（midnight）、バックアップは 30 世代保持。
- process_priority は権限不足や未対応 OS では警告を出して処理を継続する安全設計。
- .env パーサはクォート・エスケープ・インラインコメント・export プレフィックスを扱える堅牢な実装。
- Paper 検証レポートは P95 を含む複数の品質指標を算出し、閾値に基づいて総合判定（PASS / FAIL）を行う。

開発者向けヒント
- .env の自動読み込みで想定しない上書きを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してテスト実行を行ってください。
- 本番環境での起動前に python -m kabusys.validate_config を実行し、設定や YAML ファイルの整合性を確認してください。
- ロギングでファイル出力がされない場合は LOG_DIR の権限／作成状況を確認してください。作成に失敗した場合は stdout のみで動作します。

---
（注）本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴や仕様書と完全には一致しない可能性があります。
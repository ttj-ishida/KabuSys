# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
初回リリース相当の内容を、コードベースから推測してまとめています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 基本バージョン 0.1.0 を追加（パッケージメタ情報: src/kabusys/__init__.py）。
- 環境設定・ローダー
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート（src/kabusys/config.py）。
  - .env の行パーサを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い、無効行スキップ）（src/kabusys/config.py）。
  - Settings クラスを導入し、アプリ設定をプロパティで提供。J-Quants / kabu API / DB パス / Paper Trading 関連設定 / 監視閾値などを取得可能（src/kabusys/config.py）。
  - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）の分離設定を実装。
- 設定関連 CLI
  - 対話式設定ウィザードを実装（.env の初期作成・更新支援）。シークレットマスク表示・デフォルト値・選択肢をサポート（src/kabusys/config_setup.py）。
  - 設定検証ツールを実装（必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在とパースチェック。--strict オプションで警告を失敗扱いに）（src/kabusys/validate_config.py）。
- 実行系・監視
  - 実行エンジン起動スクリプトを追加（run_execution.py）。paper_trading 環境では専用の MockBroker を使用し、本番 DB と分離して data/paper_trading.db（既定）を使う。実行中は停止フラグ／PID ファイル制御、スレッドで ExecutionEngine を起動する実装（src/kabusys/run_execution.py）。
  - 監視用起動スクリプトを追加（run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する（src/kabusys/run_monitoring.py）。
  - 監視データベース初期化ユーティリティ呼び出しを起動時に行う（init_monitoring_db）。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギング初期化ユーティリティを実装（setup_logging）。stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log）を設定。LOG_DIR 環境変数・引数による上書き、既存ハンドラの再設定、防護ロジックを実装（src/kabusys/utils/logging_setup.py）。
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（set_process_priority, set_cpu_affinity）。Windows / POSIX の差分を吸収し、psutil を用いた安全なフォールバック処理を行う（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み付け: select_candidates、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は警告のうえ等金額配分にフォールバック）（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中度制御・レジーム乗数: apply_sector_cap（当日売却予定の銘柄を除外できる／"unknown" セクター無視）、calc_regime_multiplier（regime に応じた multiplier、未知レジームはフォールバック）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ決定: calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。リスクベース計算、単元株（lot_size）丸め、単銘柄上限・集計キャップ（available_cash に基づくスケーリング）、cost_buffer による保守的見積り、残差の優先配分ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
  - ポートフォリオ API をパッケージ化してエクスポート（src/kabusys/portfolio/__init__.py）。
- リサーチ（ファクター計算）
  - DuckDB を使用するファクター計算モジュールの骨格を追加（calc_momentum 等を想定）。prices_daily / raw_financials テーブルに依存する設計で、戻り値は (date, code) 単位の dict リストとなる想定（src/kabusys/research/factor_research.py）。
- ツール
  - Paper Trading 用検証レポートジェネレータを追加（paper_verification_report）。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定。閾値（稼働率 99%、fill 90%、send 95%、P95 200 ms）を定義。DB パスは引数/環境変数で指定可能（src/kabusys/tools/paper_verification_report.py）。

### Changed
- 初期リリースのため該当なし（新規実装群）。

### Fixed / Robustness improvements
- 環境値の不正（MONITOR_POLL_INTERVAL の数値化失敗や 0/負値）に対して警告を出しデフォルトにフォールバックする実装を追加（監視ポーリング）（src/kabusys/run_monitoring.py）。
- .env 読み込み失敗時に警告を出す（読み込み例外を warnings.warn で通知）（src/kabusys/config.py）。
- ログディレクトリ作成失敗時にファイル出力をスキップし、標準エラーへ警告出力してコンソールログのみで継続するフェイルセーフを実装（src/kabusys/utils/logging_setup.py）。
- psutil による優先度設定や CPU affinity が利用できない環境での失敗を警告にフォールバック（src/kabusys/utils/process_priority.py）。
- DB 周りで監視テーブルが未作成の場合に備え、init_monitoring_db を冪等に呼び出して起動時にテーブル存在を保証（run_execution/run_monitoring）。

### Security
- 特になし（初期実装）

### Notes / Misc
- 設定ファイルテンプレート生成スクリプト（scripts/generate_config.py 等）が想定されている旨を validate_config が参照している（該当スクリプトは本差分からは確認できない）。
- 一部モジュール（例: factor_research）が実装途中の箇所で終端している可能性あり（コード内コメント／未完成マーカー参照）。今後のリリースで機能拡充予定。

---

追記:
- 実際のリリース向けには個別機能ごとの詳細なテスト・ドキュメント（API 仕様、CLI 使用法、環境変数一覧、既知の制約や既存データ移行手順など）を CHANGELOG と併せて整備することを推奨します。
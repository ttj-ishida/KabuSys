# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ 本 CHANGELOG はリポジトリ内のコード内容から推測して作成しています。

## [Unreleased]

### Added
- 開発・運用用 CLI / 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する仕様。 (src/kabusys/run_monitoring.py)
  - run_execution.py: 実行エンジン ExecutionEngine の起動スクリプトを追加。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 DB を分離して使用する（data/paper_trading.db）。停止フラグや PID ファイル機構を備える。 (src/kabusys/run_execution.py)

- 環境設定と検証ツールを追加
  - config_setup.py: .env の対話式ウィザードによる作成/更新ツールを追加。主要設定項目の対話入力、既存値の読み込み、保存機能を持つ。 (src/kabusys/config_setup.py)
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML の存在とパース（PyYAML があれば内容検証）などをチェックし、エラー/警告/情報を出力。`--strict` オプションで警告を失敗扱いにできる。 (src/kabusys/validate_config.py)

- 設定管理ユーティリティ
  - config.py: .env 自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を探索）と堅牢な .env パーサを実装。クォート内のエスケープ、export 形式、コメント処理に対応。各種設定プロパティ（DB パス・PID/kill フラグパス・監視閾値・環境種別判定・paper_trading 用設定など）を提供。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。 (src/kabusys/config.py)

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーを統一的に設定する関数を追加。コンソール（stdout）と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) を設定。既存ハンドラのクリア、ログディレクトリ作成のフォールバック処理を実装。 (src/kabusys/utils/logging_setup.py)
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、失敗時は警告でスキップする設計。 (src/kabusys/utils/process_priority.py)

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定、等配分・スコア加重配分を提供。スコアが全て 0 の場合は等配分にフォールバックする警告を追加。 (src/kabusys/portfolio/portfolio_builder.py)
  - portfolio/risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやレジーム不明時のフォールバックを明確化。 (src/kabusys/portfolio/risk_adjustment.py)
  - portfolio/position_sizing: allocation_method に応じた株数決定ロジックを実装（risk_based / equal / score）。単元株丸め、per-position 上限、aggregate cap によるスケールダウン、残差配分ロジックを含む。コストバッファを考慮した保守的見積りをサポート。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージから上記関数をエクスポート。 (src/kabusys/portfolio/__init__.py)

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading DB（デフォルト data/paper_trading.db）から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポートを生成する CLI を追加。P95 計算、閾値による PASS/FAIL 判定を実装。期間指定オプション（--from / --to）や DB パス指定オプションを持つ。 (src/kabusys/tools/paper_verification_report.py)

- research/factor_research.py（部分実装）
  - DuckDB 接続を受けてモメンタム等のファクターを計算するための基盤を追加（関数設計・定数群を配置）。なお一部未完（実装継続が必要）。 (src/kabusys/research/factor_research.py)

### Changed
- 起動時のプロセス優先度設定を各起動スクリプトの最初に行うよう統一。起動ログに環境情報（KABUSYS_ENV）を出力するようにした。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
- DB の扱いを明確化
  - monitoring 用の DB 初期化は冪等化（init_monitoring_db を実行）して存在を保証。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
  - paper_trading 環境では専用の SQLite を使用して本番 DB と分離する仕様に変更。 (src/kabusys/run_execution.py, src/kabusys/config.py)

### Fixed
- ロギング設定時に既存ハンドラの二重設定を防止するため、既存ハンドラを flush/close の上で削除する処理を追加。 (src/kabusys/utils/logging_setup.py)
- .env ローダのパーサを堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、無効行スキップ）し、誤った .env による破壊的上書きを防止する保護機構を実装。 (src/kabusys/config.py)
- process_priority や CPU affinity の設定で権限不足や未対応 OS の場合に例外停止せずログ警告でスキップするように変更。 (src/kabusys/utils/process_priority.py)
- run_execution/run_monitoring の停止フラグ検知ロジックを実装（data/stop_requested.flag を監視）し、安全にループを終了する。 (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)

### Security
- .env を自動ロードする際に OS 環境変数を保護（protected set）して、既存の OS 環境変数が .env によって上書きされないようにした。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。 (src/kabusys/config.py)

### Known issues / TODO
- research/factor_research.py が未完了（calc_momentum 等の実装継続が必要）。一部ファイル末尾で実装途中の痕跡あり。
- position_sizing の価格欠損（price が 0.0）時のフォールバックロジックは TODO コメントで改善予定（前日終値や取得原価のフォールバック検討）。 (src/kabusys/portfolio/position_sizing.py, src/kabusys/portfolio/risk_adjustment.py)
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を省略するが、その際の外部通知手段は未整備。

---

## [0.1.0] - 2026-04-19

初回公開相当の機能セット（コードベース解析からの推定）:

### Added
- パッケージ基本情報（__version__ = "0.1.0"）。 (src/kabusys/__init__.py)
- 上記に挙げた起動スクリプト、設定管理、検証ツール、ロギング/プロセスユーティリティ、ポートフォリオ構築ロジック、Paper Trading 検証ツール等のコア機能を追加。 (各ファイル参照)

### Changed / Fixed
- 初期バージョンとしての各種妥当性チェック、フォールバック、エラーハンドリングを整備。上記 Unreleased の項目と重複する変更点は参照のこと。

---

（以降のバージョンについては実装の進展、バグ修正、機能追加に応じて追記してください。）
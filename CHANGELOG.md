# Changelog

すべての重要な変更を記録します。本ドキュメントは「Keep a Changelog」フォーマットに準拠しています。

注: 以下は提示されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。プロセス優先度の設定、DB 接続、ブローカーの生成、OrderManager / RiskManager / Reconciler の組み立て、エンジン実行（スレッド化）および停止フラグ監視を行う。
  - run_monitoring.py: SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを監視して安全にループを終了する。

- 環境/設定管理
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数を保護）、.env パースの堅牢化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）および各種設定プロパティ（DB パス、paper_trading 用 DB、ログレベル、閾値など）を提供。設定値の妥当性検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py: 対話式ウィザードで .env を生成/更新するツールを追加。シークレットのマスク表示、既存値の読み込み、保存確認をサポート。

- 設定検証ツール
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の検証、ログレベルの確認、DB パスの親ディレクトリチェック、YAML ファイルの存在と（PyYAML があれば）パース検証、live 環境向けのガードチェックを行う。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップするフェールセーフを実装。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定のユーティリティを追加。Windows / POSIX を吸収する実装で、権限不足や未対応 OS を安全にスキップする。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）および市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知のセクターは制限対象外、未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py: 各銘柄の発注株数を算出する関数（calc_position_sizes）を実装。allocation_method として "risk_based", "equal", "score" をサポート。単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）と残差に対する再配分ロジック、cost_buffer（スリッページ/手数料見積り）を考慮。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95））を集計してレポートを出力する CLI を追加。閾値による PASS/FAIL 判定を備える。

- その他
  - パッケージ初期化ファイル __init__.py にバージョン (0.1.0) と公開 API を定義。
  - monitoring テーブルの初期化関数 init_monitoring_db を run スクリプト起動時に冪等に呼び出して監視テーブルの存在を保証。

### Changed
- DB の扱いに関する挙動明確化
  - run_monitoring は KABUSYS_ENV にかかわらず本番向け sqlite_path（settings.sqlite_path）を使用して監視データを記録する仕様に明示（監視データを本番 DB と共有する設計）。一方、run_execution は paper_trading 環境時に専用データベース（settings.paper_sqlite_path）を使用して本番 DB と分離する。

- .env 自動ロードの挙動
  - OS 側の既存環境変数は保護され、.env/.env.local からの上書きを防止する設計。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

### Fixed
- 安全性・堅牢性の向上
  - logging_setup: 既存ハンドラを安全に flush/close してから再設定するように修正（多重ハンドラ防止）。
  - process_priority / set_cpu_affinity: 権限不足や未実装機能で例外が発生してもプロセスを継続できるように警告ログでスキップする実装に。
  - run_execution / run_monitoring: 起動直後にプロセス優先度を先に設定するよう順序を明確化。停止フラグファイル検出による安全な終了ロジックを追加。

### Security
- .env ファイル生成時の注意喚起を config_setup.py に追加（.env を Git にコミットしない旨の注記）。
- シークレット入力はウィザード上でマスク表示（画面表示時のみ）されるが、ファイルに平文で保存する点はユーザーに注意を促す文言を表示。

---

## [0.1.0] - 2026-04-23

初回リリース相当の機能群を収録。

### Added
- 基本的な自動売買フレームワークのコアユーティリティ群を実装:
  - 実行系: run_execution.py（ExecutionEngine 起動スクリプト）
  - 監視系: run_monitoring.py（SystemMonitor ポーリング）
  - 設定管理: config.py, config_setup.py, validate_config.py
  - ロギング / プロセス制御: utils/logging_setup.py, utils/process_priority.py
  - ポートフォリオ構築: portfolio/*（候補選定、重み付け、リスク調整、数量決定）
  - 研究用ファクター計算（骨格）: research/factor_research.py（モメンタム等の計算ロジックの骨組み）
  - Paper Trading 検証レポート: tools/paper_verification_report.py

### Changed
- パッケージの __version__ を 0.1.0 に設定。

### Fixed
- 初回安定稼働に向けた基本的な例外処理・安全停止処理を追加。

---

注意:
- research/factor_research.py はファイル末尾が途中で切れており、モメンタム計算の実装が未完の箇所が存在する可能性があります（開発中のモジュールとして扱われている）。
- 実装の多くは外部依存（psutil, duckdb, PyYAML など）を想定しており、実行環境に依存します。README やドキュメントで依存関係を明記することを推奨します。
# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23
初回リリース（推測）。日本株自動売買システム「KabuSys」の基本的な実行／監視／設定ツール群、ポートフォリオ構築ロジック、ユーティリティ、ペーパートレード検証ツール、および研究用ファクタ計算モジュールの骨組みを追加。

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）で本番 DB と分離して動作する。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）の検出でループを終了。
- 設定管理
  - src/kabusys/config.py: .env / .env.local の自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）、Settings クラス（環境変数の型チェック・デフォルトを含むプロパティ群）を追加。
  - src/kabusys/config_setup.py: .env を対話的に作成・更新するウィザード CLI を追加。
  - src/kabusys/validate_config.py: .env と config/*.yaml の事前検証 CLI を追加（--strict で警告を失敗扱いにできる）。
- ポートフォリオ構築（純関数）
  - src/kabusys/portfolio/portfolio_builder.py: 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - src/kabusys/portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の配分方法、単元株丸め、aggregate cap によるスケールダウンを実装。
  - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
- 監視・実行周辺
  - monitoring_db/init, SystemMonitor（参照しているが実装ファイルは別）を呼び出す起動フローを追加。監視は本番 sqlite_path を環境にかかわらず使用する設計。
  - execution 側で BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager を組み合わせてセッション実行を行うフローを追加。
- ツール
  - src/kabusys/tools/paper_verification_report.py: ペーパートレード用 SQLite を解析し、稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算して PASS/FAIL 判定を行うレポート生成スクリプトを追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 latency 200 ms）を定義。
- ユーティリティ
  - src/kabusys/utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保存）を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS の場合はスキップして警告出力。
- 研究用ファクター計算
  - src/kabusys/research/factor_research.py: DuckDB の prices_daily/raw_financials を使ったモメンタム／ボラティリティ等のファクター計算モジュールの骨組み（モメンタム計算など）を追加（設計方針、定数、関数インターフェースを含む）。
- パッケージ情報
  - src/kabusys/__init__.py: バージョンを "__version__ = '0.1.0'" として追加。

### Changed
- ログ出力の統一
  - すべての起動スクリプトで setup_logging(app_name=...) を呼び出す前提となるログ設定を導入し、ログ出力のフォーマット・ローテーションを標準化。
- 環境変数の読み込み優先度
  - OS 環境変数 > .env.local > .env の順でロードする挙動を仕様化。既存環境変数を保護するため protected セットを導入。

### Fixed / Hardened
- MONITOR_POLL_INTERVAL の安全な扱い
  - run_monitoring のポーリング間隔を MONITOR_POLL_INTERVAL（環境変数）で上書き可能にし、不正値（0 以下や非数）の場合は警告を出してデフォルト（60 秒）にフォールバックするように実装。
- 起動時のプロセス優先度設定を開始時点で行う
  - run_execution / run_monitoring の冒頭で set_process_priority("high") を呼び出し、重要プロセスとして優先度を上げる設計に変更。権限不足や未対応 OS は警告で継続。
- DB 分離の明確化
  - 実行エンジンは paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（data/paper_trading.db をデフォルト）を使用して本番 DB と完全に分離するように実装。
  - 監視は環境に関係なく monitoring 用 sqlite_path（Settings.sqlite_path）で動作するように明示。
- ログハンドラ作成の頑健性
  - ログディレクトリの作成失敗またはファイルハンドラ作成失敗時は、ファイル出力を無効化して StreamHandler のみで継続し、エラーにより起動不能にならないように対処。
- .env パーサの強化
  - export プレフィックスやシングル／ダブルクォート内のエスケープ、行内コメントの扱いなどをサポートする .env パーサが追加され、より実用的な .env 読み込みを実現。
- process_priority / cpu_affinity の失敗安全化
  - 権限がない場合や未対応の OS での呼び出しを捕捉して警告を出し、プロセスの実行を妨げないように実装。

### Documentation / CLI
- 設定ウィザード（config_setup）と検証ツール（validate_config）の追加により、初期セットアップと起動前チェックが容易に。
- paper_verification_report による定量的なペーパートレード検証フローを提供（コマンドライン引数で期間指定可）。

### Notes / Known issues / TODO
- factor_research.calc_momentum の実装はファイル末尾で途中（コメント末尾のコード切れ）となっており、完全実装は未完。研究用ファクター群は設計・骨子が含まれるが、追加実装／テストが必要。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積になる旨の TODO があり、フォールバック価格（前日終値等）を用いる改善が検討されている。
- paper_fill_mode の設定は検証（有効値チェック）を行うが、ペーパーブローカーの実装（MockBrokerClient）における細かな挙動は別途確認が必要。
- 一部のモジュール（monitoring_db の実装、SystemMonitor、ExecutionEngine の内部実装、BrokerClientFactory 等）はこの一覧から参照されているが、CHANGELOG のソースに含まれたコード断片からは詳細を推測できないため、実装依存の振る舞いについては別途確認が必要。

### Security
- .env ファイルは機密情報（API トークン・パスワード等）を含むため「絶対に Git にコミットしない」旨の注意文を config_setup に明記。
- 設定検証時にプレースホルダ値（your_value や _here で終わる値）を検出して警告する機能を追加。

---

今後のリリースでは以下を想定しています（優先度高）:
- factor_research の完全実装・単体テスト整備
- monitoring_db / SystemMonitor / ExecutionEngine 等のエンドツーエンドテスト
- ペーパーブローカーの振る舞いを明文化しテストで検証
- 単体テスト・型チェック（mypy）・CI/CD ワークフローの整備

（この CHANGELOG は、提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差分がある可能性があります。）
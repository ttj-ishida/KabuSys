# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
バージョン番号はパッケージの __version__ を参照しています。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回リリース。日本株自動売買システム KabuSys の基本機能群を追加しました（設定管理、起動スクリプト、ログ・プロセス制御ユーティリティ、ポートフォリオ構築ユーティリティ、Paper Trading 検証ツール、検証/設定ウィザードなど）。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定（__version__ = "0.1.0"）。 (src/kabusys/__init__.py)

- 起動スクリプト
  - 監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag によって行う。監視は環境設定にかかわらず本番用 sqlite_path を使用して初期化する。 (src/kabusys/run_monitoring.py)
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBrokerClient を想定した分離を行う。停止フラグ検知でエンジンを安全に停止する。PID ファイル管理をサポート。 (src/kabusys/run_execution.py)

- 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定（DBパス、APIトークン、監視しきい値、ログレベル、実行環境判定等）を提供。各種値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。 (src/kabusys/config.py)
  - 自動 .env ロード機構を実装（プロジェクトルートを .git / pyproject.toml で検出し、.env → .env.local の順で読み込み・上書き。ただし OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。 (src/kabusys/config.py)

- 設定補助 CLI
  - 対話式 .env 作成・更新ウィザードを提供。既存 .env の読み込み、マスク表示、デフォルト値、必須/任意項目の明示などをサポートし、.env を安全に生成する。生成時の注意事項（.env をコミットしない等）を出力。 (src/kabusys/config_setup.py)
  - 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードなどを実行。--strict で警告を失敗扱いにできる。 (src/kabusys/validate_config.py)

- ロギング・プロセス制御ユーティリティ
  - ログ設定ユーティリティを追加。コンソール出力（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリは引数・環境変数 LOG_DIR / デフォルト logs/ から決定。日次ローテーション・30日分保持。 (src/kabusys/utils/logging_setup.py)
  - プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップ。 (src/kabusys/utils/process_priority.py)

- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - 候補選定と重み付け：select_candidates（スコア降順 + タイブレーク）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限・レジーム乗数：apply_sector_cap（既存ポジションを考慮して同一セクターの新規候補を除外）、calc_regime_multiplier（"bull"/"neutral"/"bear" に対応し未知のレジームは警告の上 1.0 フォールバック）。 (src/kabusys/portfolio/risk_adjustment.py)
  - 発注株数決定ロジック：calc_position_sizes。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash） によるスケールダウン、cost_buffer による保守的見積り、残差配分の安定化ロジックを実装。 (src/kabusys/portfolio/position_sizing.py)
  - 上記のエクスポート用 __init__ を追加。 (src/kabusys/portfolio/__init__.py)

- リサーチ / ファクター計算（骨組み）
  - Momentum 等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計（calc_momentum 等の実装を含むが一部は継続実装前提）。 (src/kabusys/research/factor_research.py)

- Paper Trading 検証ツール
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を集計して検証レポートを生成するツールを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg / max / P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。コマンドライン引数 --from / --to / --db をサポート。 (src/kabusys/tools/paper_verification_report.py)

- 監視 DB 初期化
  - 監視テーブルの冪等な初期化関数 init_monitoring_db を run スクリプトから呼び出すことで、監視テーブルが存在することを保証。 (参照: src/kabusys/monitoring/monitoring_db.py の想定利用)

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報（API トークン等）は .env に保存する前提で、config_setup でシークレット項目をマスク表示するなどの注意を実装しています。なお .env をリポジトリにコミットしないよう注意文を出力します。

---

備考:
- 自動ロードされる .env の優先順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされません。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対しフォールバックし、0 以下や非整数を扱う際に安全に動作します。
- run_execution は paper_trading 用 DB を本番 DB から分離して使用するため、ペーパートレードと本番のデータは混在しません。
- ロギング設定は、ログディレクトリ作成に失敗した場合でもコンソール出力のみで継続するフェイルセーフ設計です。

今後の予定（例）:
- research/factor_research の完全実装とユニットテスト追加
- monitoring/ の詳細実装とアラート送信（LINE 連携等）
- broker クライアントのモックと統合テスト強化

（必要であれば各ファイルごとの詳細な変更点・実装意図を追記します。）
# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

なお、ここに記載した内容はソースコードから推測してまとめたものであり、リリースノート作成時に加筆・修正してください。

## [Unreleased]

（未リリースの変更なし）

## [0.1.0] - 2026-04-25

### Added
- 基本パッケージ初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag の存在で行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。別スレッドでエンジンを実行し、停止フラグで安全に終了可能。ペーパートレード環境（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、専用 SQLite DB（data/paper_trading.db）へ完全分離して記録する。
- 設定管理
  - config.py: 環境変数 / .env 読み込み機能を実装。プロジェクトルート自動検出（.git または pyproject.toml）を行い、.env と .env.local を適切な優先順で読み込む。設定値取得用 Settings クラスを提供し、各種プロパティ（DB パス、J-Quants トークン、kabu API など）と入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。
- 設定ユーティリティ / 検証
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。既存 .env 読み込み、シークレットのマスク表示、保存時の確認などを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、ログレベル、DB パス存在チェック、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）。--strict オプションで警告を失敗として扱う機能を追加。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一されたロギング設定関数 setup_logging を追加。コンソールは stdout に出力し、TimedRotatingFileHandler による日次ローテーション（30 日保持）をサポート。既存ハンドラの二重設定を防止する。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を追加。psutil を用い、失敗時は警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限適用（apply_sector_cap）、市場レジームに基づく乗数計算（calc_regime_multiplier）を実装。未知レジームはフォールバックして 1.0 を返し警告を出す。
  - portfolio/position_sizing.py: 株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。単元（lot_size）丸め、個別上限・合計上限、cost_buffer を考慮したスケールダウン処理、残差処理（lot 単位で再配分）を実装。
  - portfolio パッケージのエクスポートを追加（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
- 研究・分析補助
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（モメンタム、ボラティリティ、流動性、バリューなどを想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計（実装の一部は続きがある想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照。稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを算出し、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を出力。コマンドライン引数 --from / --to / --db をサポート。
- DB 初期化・監視連携
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_monitoring/run_execution 起動時に行い、監視用テーブルの存在を保証（冪等）。

### Changed
- ログの出力先を stdout に統一（StreamHandler を stdout に設定）。cron/task scheduler 等からのリダイレクトを考慮した設計。
- .env の読み込みロジックは .env と .env.local の優先順位を明確化（OS 環境変数 > .env.local > .env）。
- run_monitoring: 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（設計上の重要点として明示）。
- run_execution: paper_trading 実行時は paper_sqlite_path を使用して本番 DB と分離。
- process_priority.set_process_priority: OS ごとに適切な niceness / priority を設定し、許可されない場合は警告を出して安全にスキップ。

### Fixed
- .env パーサーの堅牢化: クォート付き値のバックスラッシュエスケープ対応、コメントの扱い（クォート外でのみ認識）を実装して .env の様々な書式に対応。
- logging_setup: 既存ハンドラがある場合、二重にハンドラが追加されないよう既存ハンドラを flush/close してから削除する処理を追加。

### Security
- シークレットの取り扱いに配慮: config_setup の対話表示でシークレットはマスク表示（保存時は .env に平文で書き込むが、ウィザードでは表示を隠す）。

### Notes / Potential limitations（実装上の注意）
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）がある場合、エクスポージャーを過少見積りする可能性があり、将来的なフォールバック（前日終値等）の導入が検討事項としてコメントされている。
- position_sizing:
  - lot_size は現在グローバル同一値を想定。将来的に銘柄別 lot_map へ拡張する旨の TODO がある。
- research/factor_research.py の実装は途中で切れている箇所があり、完全実装には続きが必要。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルトにフォールバックする挙動となる。

---

今後のリリースでは、下記のような追記が考えられます:
- research モジュールの完全実装（各ファクターの SQL/計算ロジック）
- テストカバレッジの追加（ユニットテスト、統合テスト）
- Broker クライアントの実装詳細（MockBroker と実実装の差分）
- ドキュメント（操作手順、運用ガイド、設定テンプレート）の整備

README やリリースノート化の際に、この CHANGELOG をベースに加筆・編集してください。
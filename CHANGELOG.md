# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初回公開リリース。コードベースから推測できる主要な機能追加・改善点をまとめます。

### Added
- 基本アプリケーションエントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプト（スレッドで実行、停止フラグ/PID 管理付き）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能。
- 設定・環境管理
  - kabusys.config: .env 自動読み込み（OS 環境変数を保護）、`.env` のパースロジック（クォート、エスケープ、コメント処理対応）。
  - Settings クラス: 各種設定値（DB パス、KABUSYS_ENV、PAPER_FILL_MODE など）をプロパティ経由で取得。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- 対話式設定ウィザード
  - config_setup.py: `.env` を対話式で作成/更新するウィザード。シークレットのマスク表示、既存値読み込み、保存機能を提供。
- 設定検証ツール
  - validate_config.py: .env および config/*.yaml の存在・基本妥当性チェック。--strict オプションで警告も失敗扱いに可能。
- 実行関連コンポーネント（設計上の組み立て）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（実装参照元は同梱想定）：run_execution での組み立てと起動フローを実装。
  - Paper Trading 時は別 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
- 監視（Monitoring）
  - run_monitoring による定期チェック、init_monitoring_db 呼び出しにより監視テーブルを保証（冪等）。
  - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
- ロギング・プロセスユーティリティ
  - utils.logging_setup: stdout ストリームハンドラ + 日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils.process_priority: Windows/Linux/Mac の差分を吸収するプロセス優先度設定（nice / HIGH_PRIORITY_CLASS）、CPU affinity 設定ユーティリティ、権限不足や未対応環境での安全なフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額・スコア重み（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 株数算出ロジック（risk_based / equal / score）、単元株（lot_size）での丸め、aggregate cap によるスケールダウンと端数処理、コストバッファ考慮。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力するレポート生成スクリプト。
- パッケージ情報
  - kabusys.__version__ = "0.1.0"

### Changed
- run_monitoring の挙動
  - 監視（monitoring）は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する設計（監視データは本番 DB に記録する意図を想定）。
- run_execution の DB 接続
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離する挙動を明確化。
- ロギング出力
  - StreamHandler は stdout を使用（cron/task scheduler での一本化を想定）。

### Fixed / Robustness improvements
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理、空行・コメント行の無視などへの対応により .env 読み込みの堅牢性を向上。
- 初期化・存在チェックの安全化
  - ログディレクトリ作成失敗時やファイルハンドラ作成失敗時にフォールバックしてコンソール出力のみで継続するように実装（可用性を優先）。
  - process priority / cpu affinity 設定は AccessDenied 等の例外を捕捉して警告を出し処理を継続。
- ExecutionEngine 起動ループの安全化
  - 起動前に停止フラグを確認して起動をスキップ。スレッド実行時に停止フラグ検知で engine.stop() を呼び出し安全に終了。

### Documentation / UX
- config_setup の対話式 UI により .env 初期作成が容易に。秘匿値は表示をマスク。
- validate_config により起動前の設定不備（必須環境変数未設定、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認・パースチェック）を事前に検出可能。

### Known issues / TODO / 注意点
- research/factor_research.py に未完成の箇所（ファイル末尾が途中で切れている/未実装の計算部分あり）。Factor 計算ロジックはまだ開発中の可能性あり。
- 一部モジュールの実装（例: monitoring.monitoring_db、monitoring.system_monitor、execution.* の一部）は本リストの import で使用されるが、提供ソースがこの差分に含まれていない場合があるため、実行時にモジュールが必要。
- position_sizing の price フォールバックについて注記あり（price が 0 の場合の過少見積り問題）。将来的に前日終値等のフォールバック実装が推奨されている。
- 単元株（lot_size）は現状グローバル共通値（デフォルト 100）で扱う設計。将来的に銘柄別 lot_map への拡張が予定されている旨の TODO コメントあり。
- PAPER_FILL_MODE の不正値は Settings で ValueError を送出するため、環境変数設定に注意が必要。
- run_monitoring は監視データを本番 DB（settings.sqlite_path）に書き込むため、テスト・開発時に意図せず本番データを書き込まないよう環境変数や DB パスの管理に注意。

### セキュリティ
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は .env に格納する想定。`.env` は絶対にリポジトリにコミットしないことを README 等で明示するよう注記あり（config_setup のヘッダコメント）。

---

今後のリリースに向けた提案（実装予定・改善案）
- factor_research の完成（DuckDB を使ったファクター群の実装完了）。
- 各種モジュールの単体テスト追加（.env パース、position_sizing のスケールダウンと端数処理、apply_sector_cap の境界ケース等）。
- 銘柄別 lot_size 対応と price のフォールバック戦略実装。
- 監視データ / 発注ログのマイグレーション・スキーマ管理（バージョン管理）。
- 実行スクリプトの systemd / Windows サービス用ユニットのサンプル追加。
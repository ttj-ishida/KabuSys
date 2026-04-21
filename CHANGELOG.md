# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。重大な変更や互換性に関わる点は明示しています。  
（以下はコードベースの現状から推測してまとめた変更履歴です）

## [Unreleased]
- 作業中: factor_research モジュールの実装が途中（ファクター計算の続き・最終整備が残存）。
- 小さな改善・リファクタリングやテスト追加が予定。

---

## [0.1.0] - 2026-04-21
初回リリース。自動売買システム KabuSys の基本コンポーネントを実装。

### Added
- CLI / 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動する。paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db を用いる（本番 DB と分離）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
  - validate_config: .env と config/*.yaml の設定検証ツールを追加。--strict オプションで警告も失敗扱いにできる。
  - config_setup: 対話式ウィザードで .env ファイルを作成・更新するツールを追加（秘密値のマスク表示、選択肢サポート等）。
  - tools/paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算し PASS/FAIL 判定を行う。

- 設定管理
  - config.Settings クラスを実装。環境変数から設定を取得する便利なプロパティ群を提供（J-Quants、kabuAPI、DB パス、Paper Trading の設定、監視しきい値、PID/KILL フラグ等）。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出 .git / pyproject.toml に基づく）。OS 環境変数を保護しつつ .env/.env.local を読み込む。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどを対応。

- ロギング & プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging を実装。stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに統一的に設定。LOG_DIR / LOG_LEVEL の環境変数を尊重。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するヘルパーを実装。Windows / POSIX の差分を吸収し、権限不足時は警告でスキップ。

- ポートフォリオ構成（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（スコア降順で上位 N）、等金額配分、スコア加重配分（スコア合計 0 の場合は等配分へフォールバック）を実装。
  - portfolio.risk_adjustment: セクター上限適用ロジック（既存エクスポージャー計算、上限超過セクターの候補除外）と市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: 各種配分方式（risk_based / equal / score）に基づく発注株数計算を実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケーリング）、コストバッファ考慮、残差に基づく追加配分ロジックを実装。

- Execution / Monitoring 周りの実装
  - Execution 側で RiskConfig のデフォルト値を設定し RiskManager を組み立てる処理を実装（最大ポジション比率、最大利用率、レート制限、サーキットブレーカー等）。
  - 実行中の停止フラグ（data/stop_requested.flag）や pid ファイルの扱い、エンジンの安全停止処理を導入。
  - 監視テーブル初期化用の init_monitoring_db 呼び出しを追加（冪等に DB スキーマを保証）。

- Research
  - research.factor_research の骨組みを追加（モメンタム / MA200 / ATR / ボリューム等の指標を DuckDB の prices_daily テーブルから計算する目的）。（実装の一部が未完／続きあり）

### Changed
- ロギング出力ポリシー
  - stdout を StreamHandler に使用する設計に変更（cron／Task Scheduler 等からのリダイレクトに配慮）。
  - 既存ハンドラを一旦 flush/close してから再設定することで二重登録を防止。

- データベースの取り扱い
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。監視（run_monitoring）は環境に関わらず sqlite_path（本番用）を参照するという仕様を明確化。

### Fixed
- .env 読み込み時の例外ハンドリングを改善（ファイル読み込み失敗時に警告を出して継続）。
- process_priority / set_cpu_affinity が権限不足や未対応プラットフォームで例外を上げないようにキャッチして警告でスキップするように修正。

### Notes / その他
- validate_config: PyYAML が未インストールの場合は YAML の検証をスキップし警告を表示する挙動。
- paper_verification_report: P95（第95パーセンタイル）算出ユーティリティを実装。期間フィルタや各種メトリクスの計算・判定ロジックを備える。
- セキュリティ/運用上の留意点として .env を Git にコミットしない旨を config_setup にて注意喚起。
- 実行中の停止制御はファイルベース（data/stop_requested.flag, data/kill.flag）で行う設計。KILL_FLAG_CLEAR_ON_START の挙動は Settings 経由で制御可能であり、本番環境での設定には注意が必要。

---

## 既知の制限 / 今後の予定
- research.factor_research の実装が途中のため、ファクター計算関連は継続作業が必要。
- 個別銘柄ごとの lot_size（単元株）を stocks マスタから取得する対応は未実装（現状はグローバル lot_size を使用）。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を使う等）は TODO として残している。
- 詳細なテスト・統合テスト、運用向けの監視アラートやリトライ戦略などは今後整備予定。

---

（この CHANGELOG は現行のソースコード構成と docstring / コメントから推定して作成しています。差分管理履歴があればより正確な履歴作成が可能です。）
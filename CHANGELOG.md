# Changelog

すべての注記は Keep a Changelog 準拠の形式で記載しています。  

※ 日付はリリース時点の想定日です。コード内容から推測して機能・変更点をまとめています。

## [Unreleased]

### Added
- 監視（monitoring）・実行（execution）用の起動スクリプトを追加
  - run_monitoring: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルによる安全停止処理を実装。
  - run_execution: ExecutionEngine を起動するラッパー。スレッドでエンジンを実行し、停止フラグで安全に停止可能。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用。

- 環境設定・検証 CLI を追加
  - config_setup: 対話式ウィザードで .env を作成/更新するツールを追加。必須/任意項目、シークレット入力、既存値の再利用などに対応。
  - validate_config: .env や config/*.yaml を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや YAML ファイルの存在チェック、live 環境向けのガード（LINE 通知設定や Kill Switch の注意喚起）を実装。--strict オプションで警告も失敗扱いにできる。

- 環境設定読み込み・管理の実装
  - Settings クラスを導入し、.env/.env.local と OS 環境変数の自動読み込み（プロジェクトルート検出ベース）を実装。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - .env のパースは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントに対応する堅牢な実装を提供。
  - 各種設定プロパティ（J-Quants、kabu API、DB パス、Paper Trading 用設定、監視閾値、ログレベル判定など）を提供。

- Execution 周りの主要コンポーネント統合点を追加
  - BrokerClientFactory（ブローカークライアントの生成）
  - ExecutionEngine / EngineConfig（実行エンジン）
  - OrderRepository / OrderManager / RiskManager / Reconciler（発注・リスク管理・整合処理）
  - paper_trading 環境では MockBrokerClient と分離された SQLite（デフォルト data/paper_trading.db）を使用

- 監視 DB 初期化ユーティリティを追加
  - init_monitoring_db により監視用テーブルが存在することを冪等的に保証

- ロギング・プロセス制御ユーティリティを追加
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定する共通ユーティリティ。ログディレクトリ作成失敗時のフォールバックも考慮。
  - process_priority: psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows / POSIX）および CPU affinity 設定関数を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio.portfolio_builder: シグナルの候補選定（スコア降順・タイブレーク）、等金額／スコア加重の重み算出
  - portfolio.risk_adjustment: セクター上限ルール適用（現保有エクスポージャー計算、当日売却銘柄除外）、市場レジームに応じた乗数（bull/neutral/bear）算出
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め（lot_size）、max_position・aggregate cap の処理、コストバッファを考慮したスケーリングと端数配分ロジック

- Paper Trading 検証レポート生成スクリプトを追加
  - tools.paper_verification_report: ペーパートレード用 SQLite からシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計しパス/フェイル判定を出力。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

- 研究用ファクタ計算モジュールの基礎を追加
  - research.factor_research: DuckDB 接続を受け、momentum（1M/3M/6M、MA200乖離）、ATR、流動性等のファクター計算基盤を実装（momentum 計算ロジックを含む。ファイル末尾で実装が続く想定）。

### Changed
- なし（新規実装群のため）

### Fixed
- なし

### Deprecated
- なし

---

## [0.1.0] - 2026-04-23

初回公開想定バージョン。上記 Unreleased に記載の機能群をまとめたバージョンとしてリリース可能。

### Added
- パッケージのバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 上記「Unreleased」の全機能（監視/実行起動スクリプト、設定管理・検証・ウィザード、ポートフォリオ構築ロジック、ロギング・プロセスユーティリティ、Paper Trading レポート、研究用ファクタ計算の骨子など）。

### Notes / Migration
- .env の自動読み込みはデフォルトで有効。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番稼働時は KABUSYS_ENV を正しく設定し、validate_config で事前確認することを強く推奨します（特に KABUSYS_ENV=live 時の注意喚起が組み込まれています）。
- run_execution は paper_trading 環境で専用 DB を使用するため、本番 DB とデータが混在しない設計です。

---

## 未解決・今後の改善案（コードに基づく提案）
- portfolio.position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）を実装すると安全性が向上する。
- research.factor_research の残り実装（ボラティリティ、流動性、正規化処理等）を完了する。
- logging_setup のファイルハンドラエラー時の通知をよりユーザフレンドリーにする（例: 起動時にログ出力先が限定されていることを明示）。
- process_priority の権限エラー時に、何が実行されていないかを CLI 起動ログ等で分かりやすくする。
- validate_config で YAML のスキーマ検証（必須フィールド・型チェック）を追加すると設定ミスをさらに減らせる。

---

以上。必要であればリリースノートの英語版や、個別ファイルごとの詳細な変更点（diff ベースの想定）も作成します。どの形式がよいか指示してください。
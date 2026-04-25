# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルは、コードベース（src/kabusys/...）の内容から推測して作成したリリースノートです。

## [Unreleased]

- 今後の改善案・想定追加機能
  - research/factor_research.py の処理完了・テスト追加（ファクター計算の残り実装）
  - リスク管理・発注ロジックの追加ユニットテスト・シミュレーションスイート整備
  - 単元サイズ（lot_size）を銘柄毎に管理するためのマスタ連携
  - DuckDB / SQLite の移行・マイグレーション管理機能

---

## [0.1.0] - 2026-04-11

### Added
- 基本アーキテクチャ・起動スクリプトを多数追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。KABUSYS_ENV により本番 / ペーパートレードの DB 分離と MockBroker の利用をサポート。停止用フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）を利用する制御ループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から期間集計レポート（稼働率、注文成功率、送信率、レイテンシ等）を生成する CLI を追加。P95 の計算や閾値判定ロジックを実装。

- 設定・環境管理
  - config.py: .env の自動読み込み（.env, .env.local）と環境変数ラッパー Settings を実装。KABUSYS_ENV / LOG_LEVEL 等のバリデーション、PAPER_FILL_MODE の検証、paper_trading 用 DB パスの取得等を提供。
  - config_setup.py: .env の対話式ウィザードを追加し、初期設定の作成・更新をサポート。秘密値のマスク表示や保存確認を実装。
  - validate_config.py: 起動前に .env と config/*.yaml の不足を検出する CLI を追加。--strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を実装（未知レジーム時はフォールバックと警告）。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的な見積りを実装。
  - portfolio/__init__.py: 上記機能をパッケージとして公開。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を用いる統一的なログ設定ユーティリティを追加。LOG_DIR の自動作成失敗時はファイル出力をスキップする耐障害性を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足や未サポート環境では警告を出して安全にフォールバック。

- Execution コンポーネント（起動スクリプトから組み立てる主要クラス呼び出し）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て例を run_execution.py に追加。RiskConfig のデフォルト等を明示。

- その他ユーティリティ・挙動
  - .env パーサーは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 環境変数自動ロード時に OS 環境変数を保護（上書き禁止）する仕組みを採用。
  - monitoring 用 DB 初期化（init_monitoring_db）は起動時に冪等に保証する処理を追加（run_execution/run_monitoring から呼び出し）。
  - 停止フラグ（data/stop_requested.flag）検知による優雅なシャットダウンを両起動スクリプトに実装。

### Changed
- （初回公開のため該当なし）

### Fixed
- ロギング設定周りでログディレクトリ作成失敗時にクラッシュしないようハンドラ生成を堅牢化（ログ出力をコンソールにフォールバック）。
- process_priority のプラットフォーム差分による Import/属性参照エラーを getattr によるフォールバックで回避し、未サポート OS では警告を出してスキップするように改善。
- run_monitoring の MONITOR_POLL_INTERVAL パースで不正値が指定された場合にデフォルト値へフォールバックし、エラーメッセージをログに出すように修正。

### Security
- .env ファイル生成スクリプトのヘッダに「.env を絶対に Git にコミットしないこと」を明示して注意喚起を追加。
- Settings._require により必須環境変数が未設定の場合は起動前に明確に失敗するようにして、秘密情報の未設定による誤動作を抑止。

---

注:
- 上記はリポジトリ内のソース（src/kabusys 以下）から機能・振る舞いを推測してまとめた CHANGELOG です。実際のコミット履歴が利用可能な場合はそれに基づく詳細な差分記述を推奨します。
# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

- 次回リリースに向けた作業中

---

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys の基礎機能を実装。

### Added
- アプリケーションのバージョンを設定
  - kabusys.__version__ = "0.1.0"

- 環境・設定管理
  - 環境変数自動読み込み（.env / .env.local）と読み込み制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - .env ファイルの高度なパーサ（export プレフィックス対応、シングル/ダブルクォート・エスケープ対応、インラインコメントハンドリング）
  - OS 環境変数を保護するロード方法（既存のキーは保護）
  - Settings クラスによる集中管理（各種パス、API トークン、ポリシー、しきい値、環境判定など）
  - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーション

- 設定支援ツール・CLI
  - config_setup: .env を対話式に作成/更新するウィザード（秘密値はマスク表示）
  - validate_config: 起動前チェック CLI（必須環境変数、パス、YAML ファイルの存在・パース確認、--strict オプション、live 環境向けガード）

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory を利用したブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、デフォルト RiskConfig 設定（max_position_pct, max_utilization, rate_limit 等）
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）の監視、デーモンスレッドで engine.run_session を実行
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一貫性のため）
    - 停止フラグ検出、例外発生時にもループ継続（ログ出力）

- 監視 DB 初期化
  - init_monitoring_db: 監視用テーブルの初期化（冪等処理を想定）

- ロギング・ユーティリティ
  - setup_logging: 全起動スクリプトで共通利用するログ初期化
    - StreamHandler を stdout に出力（cron/task のリダイレクト互換性）
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/、30 日保持）
    - 既存ハンドラをクリアして二重出力を防止
    - LOG_DIR / LOG_LEVEL の優先解決順を実装

- プロセス制御ユーティリティ
  - set_process_priority(level): psutil を用いて Windows/Linux/Mac に跨る優先度設定を提供（high/normal/low）
  - set_cpu_affinity(cpu_count): 指定コア数だけにプロセスをピン止め（対応しない環境では警告ログ）

- ポートフォリオ構築（純粋関数群）
  - portfolio.select_candidates: BUY シグナルをスコア降順で選別
  - portfolio.calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコアが全て 0 の場合は等配分にフォールバック（警告ログ）
  - risk_adjustment.apply_sector_cap: セクター集中上限チェック（既存保有時価ベース）、"unknown" セクターは除外対象外
  - risk_adjustment.calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）

- ポジションサイジング
  - position_sizing.calc_position_sizes: allocation_method("risk_based", "equal", "score") に基づく発注株数計算
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積もり
    - risk_based: 損切り幅・risk_pct によるポジション算出
    - スケールダウン時の残差配分ロジック（fractions による公平配分）

- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを生成
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出・評価（閾値判定と PASS/FAIL 表示）
    - P95 計算ユーティリティ、期間フィルタ、DB 存在チェック

- 研究用ファクター計算（骨組み）
  - research.factor_research: calc_momentum を含むファクター計算モジュールの実装開始（DuckDB 経由で prices_daily / raw_financials を参照する設計）

### Fixed
- ロギング設定の重複追加を防止するため、ルートロガーの既存ハンドラを明示的に flush/close してから削除する処理を追加
- logging のファイル出力ディレクトリ作成失敗時にプロセスが停止しないよう、FileHandler 作成失敗時はコンソール出力のみで継続する耐障害処理を追加
- .env 読み込み時に OS 環境変数を上書きしないよう保護（.env.local の override 動作も OS 環境変数は保護）

### Notes / Behavior
- run_monitoring は Monitoring 用 DB に関して "環境にかかわらず本番 sqlite_path を使用する" 設計になっているため、開発環境での監視データと本番データが混在しないよう運用時に注意してください。
- validate_config の YAML 検証は PyYAML が存在する場合のみ実行され、不在時は警告を出してスキップします。
- config_setup により生成される .env ファイルには機密情報が書き込まれるため、絶対にリポジトリにコミットしないでください（ヘッダにもその旨を明記）。

### Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり（前日終値や取得原価でのフォールバック検討）
- position_sizing: 将来的に銘柄別の lot_size をサポートするための拡張 TODO（現状は共通 lot_size を想定）
- research.factor_research.calc_momentum の実装はソースが途中で切れている（今後の実装・テストが必要）

---

## セマンティックバージョニング方針
- 互換性のない API 変更はメジャーアップデート（MAJOR）、
- 後方互換のある機能追加はマイナーアップデート（MINOR）、
- バグ修正や小さな改善はパッチ（PATCH）としてリリースします。

---

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時は必要に応じて調整してください。）
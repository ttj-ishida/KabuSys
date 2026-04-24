# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 基本パッケージ初版を実装。
  - パッケージメタ情報: kabusys __version__ = 0.1.0 を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を使用し、data/paper_trading.db（または環境変数で指定したパス）に記録することで本番 DB と分離。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に依らず production の sqlite_path を使用する仕様を明記。
    - プロセス優先度設定、停止フラグの検知、例外発生時のログ記録を行う。
- 環境設定 / 検証
  - config.py: 環境変数読み込み・管理モジュールを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数は保護）。
    - .env 行のパースを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等）。
    - 各種設定プロパティ（DB パス、Paper Trading 用パス、しきい値、KABUSYS_ENV/LOG_LEVEL の検証等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - シークレット入力マスク、選択肢サポート、既存 .env の読み込みと Enter による継承、保存前確認を実装。
  - validate_config.py: 起動前に .env と config/*.yaml の基本検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）などを検証。--strict で警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB（SQLite）から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率(send rate)、レイテンシ（avg/max/P95）などを集計し PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）および --db オプションをサポート。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。
    - スコアが全て 0 の場合は等重配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限の適用とレジーム乗数計算（apply_sector_cap, calc_regime_multiplier）を実装。
    - セクター上限を超過している場合は新規候補を除外。未知セクター("unknown")は上限除外対象外。
    - レジームに応じた乗数 (bull/neutra/bear) を提供し、未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: 発注株数計算ロジック（calc_position_sizes）を実装。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株 (lot_size)、max_position_pct、max_utilization、cost_buffer に基づく aggregate cap、スケーリング、端数処理（lot 単位）を実装。
- ユーティリティ
  - utils/logging_setup.py: 全体で使うログ設定ユーティリティを追加。
    - StreamHandler（stdout） と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度設定および CPU affinity 設定ユーティリティを追加（psutil を使用）。
    - Windows/Linux(macOS等POSIX) を吸収する実装。権限不足などで失敗した場合は警告ログでスキップ。
- モニタリング DB の初期化用ユーティリティ（monitoring.monitoring_db.init_monitoring_db）や SystemMonitor / ExecutionEngine 等の基盤コード（呼び出し元を含む）を追加（スクリプトから使用）。
- research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム等の定義と計算方針を含む）。DuckDB を使った計算を想定。

### 変更 (Changed)
- ロギング
  - デフォルトのログディレクトリとファイル名ルールを統一（logs/<app_name>.log、日次ローテーション）。
  - コンソール出力は stderr ではなく stdout を使用（cron/Task Scheduler 等とのリダイレクト容易化）。
  - ログレベル解決順を明文化（引数 > 環境変数 > デフォルト）。
- DB 接続ポリシー
  - 監視モジュールは環境に依らず本番 sqlite_path を使用する旨を明確化（監視は常に本番 DB を観察する設計意図）。
  - 実行エンジンは paper_trading の場合に専用の paper_sqlite_path を使用して本番 DB から分離。
- .env 自動読み込み
  - プロジェクトルート検出に .git / pyproject.toml を使用することで配布後の挙動の安定化を図る。
  - OS 環境変数が既に存在する場合は上書きしない（.env.local は明示的に override 可、ただし OS 環境変数は保護）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの除去などに対応して .env の誤読を減らす実装に改良。
- MONITOR_POLL_INTERVAL の値検証を追加
  - 0 以下や非整数が指定された場合に警告を出してデフォルト値（60 秒）にフォールバックするように修正。
- プロセス優先度 / CPU affinity 設定の例外ハンドリングを追加
  - 権限不足や未対応 OS に対して安全にフォールバックし、起動不能にならないようにした。
- 監視 DB 初期化の冪等性
  - run_execution で起動時に監視テーブル存在を保証する init_monitoring_db 呼び出しを追加（重複実行でも安全）。
- paper_verification_report: DB が存在しない／テーブルがない場合に OperationalError をキャッチして N/A を返す等、堅牢性を向上。

### 注意事項 / 既知の制限 (Known issues)
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格がない（0.0）場合、エクスポージャーが過少見積りされる可能性があるため将来の拡張でフォールバック価格の採用を検討と注記あり。
- research/factor_research.py はファイル末尾が途中で切れている（骨格実装の一部で、完全実装は継続予定）。
- 一部機能は psutil や PyYAML 等の外部依存に依存しており、環境にインストールされていない場合は機能限定（例: YAML 検証スキップ、CPU affinity の無効化）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないこと。

### セキュリティ (Security)
- 機密情報（J-Quants トークン、kabu API パスワード等）は .env で管理することを前提としており、config_setup による .env 生成時にも明示的に注意喚起を表示。

---

将来的なリリースでは、factor_research の完全実装、ExecutionEngine / SystemMonitor 周りの詳細なテストとドキュメント拡充、銘柄別 lot_size 対応などを予定しています。
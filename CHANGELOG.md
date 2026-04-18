# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

最新の変更は一番上に記載しています。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワーク「KabuSys」のベース機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py, version="0.1.0"）。
  - プロジェクトルート検出ロジックを実装し、.env 自動ロードをサポート（src/kabusys/config.py）。
  - .env ファイルの堅牢なパース実装（クォート、エスケープ、export プレフィックス、インラインコメントの扱いを含む）。

- 設定管理 / CLI
  - Settings クラスを実装し、環境変数から各種設定（DB パス、API トークン、環境種別、しきい値など）を取得できるようにした（src/kabusys/config.py）。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・編集を補助（シークレット入力、デフォルト値、選択肢サポート）。
    - 保存プレビューおよび確認フローを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向け追加警告等を実施。
    - --strict オプションで警告を失敗扱いにするモードを提供。

- ログ / プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力を構成。
    - LOG_DIR / LOG_LEVEL の考慮、既存ハンドラのクリアに対応。
  - プロセス優先度／CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS 等）差分を吸収。アクセス権限例外を安全にハンドリング。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。

- 実行系（Execution）と監視（Monitoring）
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - PID ファイル管理・停止フラグ（data/stop_requested.flag）監視ロジックを実装。
    - リスク設定（RiskConfig）にデフォルト値を設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 関連など）。
  - Monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ監視、例外時のログ出力保持、DB（SQLite / DuckDB）接続・クローズの管理。
  - 監視 DB 初期化処理を呼び出す init_monitoring_db を利用（冪等にテーブル作成を保証）。

- ポートフォリオ構築（Portfolio）
  - 候補選定と重み計算（pure functions）
    - select_candidates（スコア降順、signal_rank によるタイブレーク）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_equal_weights（等金額）／calc_score_weights（スコア正規化、全スコアが 0 の場合は等配分にフォールバック）を実装。
  - リスク調整（pure functions）
    - apply_sector_cap：既存ポジションのセクター別エクスポージャーからセクター集中上限をチェックし、超過セクターの候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームは警告のうえ 1.0 にフォールバック。
  - ポジションサイジング（pure functions）
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数決定ロジックを実装。
      - risk_based: リスク許容量（risk_pct）と stop_loss_pct による単位株数計算。
      - equal/score: 重みと max_utilization に基づく割当計算。
      - lot_size（単元）丸め、per-stock 上限（max_position_pct）適用。
      - aggregate cap（available_cash を超える場合）のスケーリングと、残余キャッシュを用いた再配分（fractional remainder 優先順）を実装。
      - cost_buffer を考慮した保守的なコスト見積りをサポート。
  - portfolio パッケージのエクスポート定義を追加（src/kabusys/portfolio/__init__.py）。

- 研究 / ファクター計算
  - factor_research モジュール（src/kabusys/research/factor_research.py）を追加。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、流動性等を意図した計算関数群の骨子を実装。DuckDB 接続を受け取り prices_daily / raw_financials に基づく計算を行う方針。
    - （注）ファイル終端で実装が途中になっている関数あり（今後の実装予定を示唆）。

- ユーティリティ / ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（paper_trading.db）を走査して、稼働率、注文成立率（fill rate）、送信率、P95 レイテンシ等を集計・レポート出力。
    - 基準値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションを備え、環境変数 PAPER_TRADING_SQLITE_PATH を参照可能。

- DB / 分析
  - DuckDB を分析用に利用する設計（各種モジュールで duckdb 接続を受け取る）。
  - monitoring 用の SQLite DB と paper_trading 用の SQLite を明確に分離（paper_trading モード時）。

- 安全装置 / 運用
  - 起動時にプロセス優先度を "high" に設定する呼び出しを標準起動フローに組み込み（run_execution.run_monitoring で set_process_priority("high") を呼出し）。
  - 停止フラグ（data/stop_requested.flag）および PID/kill フラグ周りの取り扱いを実装。
  - Logging 設定失敗時はファイル出力をフォールバック（console のみ）するように堅牢化。

### Changed
- 新規プロジェクト初期実装のため該当なし。

### Fixed
- 新規プロジェクト初期実装のため該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数にシークレット（API トークン、パスワード）を使用するため .env を絶対にコミットしない旨を config_setup の生成ヘッダに明記。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。将来のコミット履歴や意図せぬ実装差異がある場合があります。必要に応じてリリース日や項目を調整してください。
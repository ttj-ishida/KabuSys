# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

全般:
- セマンティックバージョニングを想定（パッケージ版の __version__ は 0.1.0）。
- 本ログはコードベースの内容から推測して作成しています。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 初回リリース（推定）
公開日: 未設定

### Added
- 基本パッケージ構成
  - kabusys パッケージの初期モジュールを追加。__version__ = "0.1.0" を設定。

- 設定管理
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env ファイルのパース実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、環境変数経由で各種設定にアクセス可能（J-Quants トークン、kabu API、DB パス、紙トレード設定、監視閾値、ログレベルなど）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。

- 環境セットアップ / 検証コマンドライン
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を提供。秘匿値のマスク表示、デフォルト/選択肢対応。
  - validate_config: .env や config/*.yaml の検証 CLI を提供。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML が存在する場合）の検証、live 環境向けのガードメッセージ、--strict モードをサポート。

- ロギング / プロセスユーティリティ
  - setup_logging: ルートロガーを統一設定するユーティリティを提供。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL の優先解決、30日分のローテーション保持。
  - process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティ。Windows/Linux/macOS を考慮し、CPU affinity 設定関数も提供。権限不足時は警告でスキップ。

- 実行/監視エントリポイント
  - run_execution: 実行エンジン起動スクリプトを追加。特徴:
    - プロセス優先度を高に設定。
    - KABUSYS_ENV が paper_trading の場合、paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory により実環境 / モックブローカーを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を初期化・起動。スレッド実行と停止フラグ（data/stop_requested.flag）での安全停止をサポート。
    - Execution 用 PID ファイル管理（data/execution.pid）を使用。

  - run_monitoring: 監視ループ起動スクリプトを追加。特徴:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境に関わらず本番 sqlite_path を使用（監視データは単一 DB に集約）。
    - SystemMonitor の check_once を定期実行し、例外は捕捉して次ポーリングへ継続。停止フラグでループ終了。

- 監視 DB 初期化
  - init_monitoring_db を利用して起動時に監視用テーブルが存在することを保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（DB 参照なし、メモリ内計算）。
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順かつ signal_rank によるタイブレークで上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等比率およびスコア加重配分。スコア合計が 0 の場合は等配分へフォールバック（警告）。
    - risk_adjustment:
      - apply_sector_cap: 既存保有のセクターエクスポージャーに基づき、最大セクター比率超過時に新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market レジームに応じた投下資金の乗数（bull/neutral/bear をサポート、未知値は警告・1.0 フォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した発注株数計算。損切り率・リスクパーセント・単元（lot_size）丸め・max_position_pct・max_utilization・コストバッファ（手数料/スリッページ見積り）を考慮。投資合計が利用可能現金を超えた場合のスケーリングと残差補正ロジックを実装。

- 研究用ファクター計算（下流で DuckDB を使用）
  - research/factor_research: momentum/value/volatility/liquidity 等のファクター計算を設計（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。関数群のスケルトンと定数を用意（モメンタム期間、ATR、ボリュームウィンドウ等）。※ファイルは途中まで含まれている（続きありを想定）。

- ペーパートレード検証ツール
  - tools/paper_verification_report: paper trading 用 SQLite DB を元に検証レポートを生成する CLI を追加。指標:
    - システム稼働率（uptime %）、エラー数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - レイテンシ（平均/最大/P95）
  - デフォルト閾値に基づく PASS/FAIL 判定を実装（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。期間フィルタ（--from / --to）や --db オプションをサポート。

- DB 接続
  - sqlite3 と DuckDB 双方の接続を想定し、実行／監視で両方を使用。duckdb は分析用途、sqlite は監視・履歴用途として扱う想定。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- なし

### Removed
- なし

### Security
- 秘匿情報（API トークン等）は Settings 経由で環境変数から取得し、config_setup では .env に保存する際に注意喚起（.env を Git にコミットしないようドキュメント内に明記）。

---

注記:
- 上記は提供されたソースコードの構造・ドキュメント文字列・ロジック・環境変数名から推測して作成した CHANGELOG です。実際のリリース日やリリースノートの厳密な内容はリポジトリの履歴（git タグ / リリースノート）に従ってください。必要ならリリース日や追加の修正点を反映した更新版を作成します。
# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従って記載しています。

- フォーマット: MAJOR.MINOR.PATCH
- 日付はコミット/リリース日に合わせて付与してください（ここではコードベースから推測した初期リリースとして記載しています）。

## [Unreleased]

### Added
- なし（開発中の変更をここに記載してください）

---

## [0.1.0] - 初期リリース（推測）
初期公開（コードベースから推測）。自動売買システムのコアユーティリティ、CLI、ポートフォリオ構築ロジック、モニタリング/実行エンジン起動スクリプト、検証ツールなどを含む。

### Added
- 環境設定・管理
  - .env ファイルの自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml を基準）を実装。OS 環境変数を保護しつつ `.env` / `.env.local` を読み込む。
  - .env の柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - Settings クラスを導入し、アプリケーション設定（DB パス、API トークン、Paper Trading 設定、監視閾値、環境判定等）をプロパティ経由で安全に取得可能にした。
  - 環境設定ウィザード CLI（config_setup）を追加。対話式で .env を初期生成/更新（シークレットマスク表示、既存値の再利用、デフォルト選択肢の提示）。
  - 設定検証 CLI（validate_config）を追加。.env と config/*.yaml の存在や基本構成を検証する機能を提供（--strict オプションで警告も失敗扱いに）。

- 実行 / 監視
  - run_execution 起動スクリプトを追加。ExecutionEngine 起動ロジック、Paper Trading 時の専用 DB 分離（data/paper_trading.db を使用）、BrokerClientFactory 経由のブローカークライアント作成、OrderManager / RiskManager / Reconciler の組み立て、PID ファイルおよび停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring 起動スクリプトを追加。SystemMonitor のポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を利用して冪等にテーブルを保証。

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）を追加。Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）から集計を行い、稼働率・注文成功率・送信率・レイテンシ（P95 など）を算出して PASS/FAIL 判定を出力する。日付フィルタ指定、NULL 安全な集計、P95 計算ロジックを備える。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder:
    - シグナル選定関数 select_candidates（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等金額・スコア加重ウェイト計算（calc_equal_weights, calc_score_weights）。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment:
    - セクター集中制限 apply_sector_cap（既存保有のセクター露出を計算し上限超過セクターの新規候補を除外）。"unknown" セクターは制限を適用しない設計。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear にマップ、未知レジームは警告の上フォールバック）。
  - portfolio.position_sizing:
    - 株数算出ロジック calc_position_sizes（allocation_method 指定により "risk_based" / "equal" / "score" をサポート）。単元株（lot_size）丸め、1 銘柄上限、全体の aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残差処理で lot_size 単位の追加配分などを実装。

- リサーチ / ファクター計算
  - research.factor_research モジュールを追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照して以下を計算:
    - Momentum ファクター（1M/3M/6M リターン、200 日 MA 乖離率）、ウィンドウ不足時は None を返却。
    - Volatility / Liquidity 指標（ATR、平均売買代金、出来高比など）、NULL 伝播を適切に制御するクエリ設計。
  - パフォーマンス考慮で DuckDB の Window 関数を活用し、営業日ベースの窓長を設定。

- ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）。Windows / POSIX（Linux, macOS, FreeBSD）に対応し、権限不足・未実装 API は警告でスキップ。CPU affinity 設定関数 set_cpu_affinity も実装。

- パッケージ初期設定
  - パッケージメタ情報 __version__ = "0.1.0" を定義し、主要モジュールを __all__ で公開。

### Changed
- なし（初期リリースのため変更履歴なし）

### Fixed
- なし（初期リリースのため修正履歴なし）

### Security
- なし（特にセキュリティ修正は検出されていません）

---

注意:
- この CHANGELOG は提供されたソースコードから機能や設計を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに従って日付やカテゴリを更新してください。
- 設定値や閾値（例: ポーリング間隔デフォルト 60 秒、リスクパラメータ、検証基準等）はコード内のコメント・定数に基づいて記載しています。必要に応じて運用ポリシーに合わせて調整してください。
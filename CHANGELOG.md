# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
各バージョンの説明は、リポジトリ内のコード（モジュール構成・実装・ドキュメント文字列）から推測して作成しています。

なお、本CHANGELOGはコードから推定した初期リリース相当の機能一覧および実装上の注意点をまとめたもので、実際のコミット履歴に基づくものではありません。

## [Unreleased]

- （現時点: なし）

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初期リリース相当の機能セットを追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に探索し、OS 環境変数を保護しつつ環境変数をロードする挙動を採用。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - Settings クラスを導入し、各種設定値（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境モード 等）をプロパティとして提供。値検証（有効値チェック、必須環境変数チェック）を行う。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性検査を実装。
- 実行エンジン関連
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して実際のブローカークライアント（または MockBrokerClient）を生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、別スレッドでセッションを実行。停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を利用した安全な停止処理を実装。
    - RiskManager 初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入。
- 監視関連
  - run_monitoring: SystemMonitor ポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値に対しては警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（設計上の決定として明示）。
    - stop flag によるグレースフルシャットダウンをサポート。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを統一（process priority のユーティリティを使用）。
    - duckdb と sqlite の接続確立および監視 DB 初期化処理を含む。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。未知レジームはフォールバック動作（1.0）で警告。
  - position_sizing: 各銘柄の発注株数算出（calc_position_sizes）を実装。allocation_method は "risk_based" / "equal" / "score" をサポートし、単元株（lot_size）、手数料・スリッページ想定（cost_buffer）、aggregate cap によるスケーリング、端数処理（lot_size 単位）を扱う。
- 研究（Research）モジュール
  - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）ファクター計算を DuckDB SQL ベースで実装。入力は prices_daily / raw_financials テーブル。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）等を標準ライブラリのみで実装。スピアマンのランク相関（ties の平均ランク処理）をサポート。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）と上記関数群をエクスポートする。
- AI / ニュース NLP
  - ai.news_nlp: raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントスコア（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション、スコアクリッピング（±1.0）、部分失敗時の DB 保護（対象コードのみ置換）などフェイルセーフ設計を採用。
    - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 を UTC に変換）を実装。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を提供。psutil の例外に対するフォールバック（警告）を実装。
  - set_cpu_affinity を実装し、指定コア数で CPU affinity を固定する機能を追加（利用不可時は警告でスキップ）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を算出し PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB パスの引数指定に対応。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルが存在することを保証（冪等）。

### Changed
- 設計上の決定（ドキュメント化）
  - 監視コンポーネントは KABUSYS_ENV に関係なく本番 sqlite_path を参照する仕様を明文化（run_monitoring のモジュール docstring）。
  - run_execution は paper_trading 環境を明確に本番と分離する挙動を採用（専用 DB）。
- エラーハンドリングの強化
  - ポーリングループ内 check_once() の例外をログに出して次回ポーリングへ継続するフェイルセーフ実装（監視ループ）。
  - DuckDB/SQLite のクエリで OperationalError が発生した場合にレポート生成がデグレードして継続する実装（paper_verification_report）。

### Fixed
- 環境変数読み込みまわりの堅牢化
  - .env パーサのクォートやエスケープ処理を改良し、export プレフィックスや行末コメントの扱いで誤認されにくくした。
  - 自動ロード時にプロジェクトルートが見つからない場合は安全にスキップするよう修正。
- データ不足ハンドリング
  - factor_research 等でウィンドウ不足時に None を返すことで、上位処理が例外で中断しないように設計。

### Deprecated
- （現時点: なし）

### Removed
- （現時点: なし）

### Security
- OpenAI API キーの取り扱いは環境変数または引数経由で渡す設計。キー未設定時は明示的に ValueError を発生させるようにしている。

---

注記 / 実装上の既知事項（コード内コメントより抜粋・要約）
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合は現状ではエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO がある。
  - "unknown" セクターはセクター上限判定の対象外（除外しない）という仕様。
- portfolio.position_sizing:
  - 単元株（lot_size）は現状グローバル固定で実装。将来的に銘柄別 lot_size を導入する余地あり。
  - aggregate cap のスケーリング時に整数単元（lot_size）で丸めと残差配分を行うアルゴリズムを実装。
- ai.news_nlp:
  - 実装は堅牢性（再試行・部分更新・検証）を重視しているが、外部 API 呼び出しに伴うコスト・レイテンシは運用上の注意が必要。
- run_monitoring / run_execution:
  - stop flag（data/stop_requested.flag）と PID ファイルを用いた外部からのプロセス制御に対応している。
  - run_monitoring は MONITOR_POLL_INTERVAL の不正な値に対してデフォルトへフォールバックし、ログに警告を出す。

もし実際の変更履歴（コミット単位）やリリース履歴が必要であれば、git ログ等のソース履歴を提供してください。実際の履歴に基づいてより正確な CHANGELOG を生成できます。
# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
本ファイルはコードベース（src/ 以下）から推測して作成した変更履歴です。

全般:
- 初期リリース相当の機能群をまとめています（バージョン 0.1.0）。
- 日付はこの CHANGELOG 作成日（2026-04-17）を用いています。

## [Unreleased]
- （作業中 / なし）

---

## [0.1.0] - 2026-04-17

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - モジュール構成を整備（data, strategy, execution, monitoring, portfolio, research, ai, tools, utils 等のサブパッケージ）。

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して MockBroker を利用する設計。
    - ExecutionEngine の起動前に stop フラグをチェックし、安全にスレッド起動・監視・停止を行う。
    - Execution 用の PID 管理（data/execution.pid）をサポート。
    - Execution 起動時に依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて ExecutionEngine に渡す。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、初期 portfolio value を broker.get_available_cash() から設定する。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告してデフォルトを使用。
    - Monitoring は環境にかかわらず本番 sqlite_path を参照（監視データは本番用に集約）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、例外捕捉でループ継続を実装。
    - 起動時にプロセス優先度を high に設定する処理を追加（プラットフォーム差分は utils/process_priority が吸収）。

- 設定
  - config.py: 環境変数読み込み・管理を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を行い、.env / .env.local を自動で読み込む（OS 環境変数は保護）。
    - .env パーサの強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスを追加し、各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、env/log レベル判定、paper_fill_mode のバリデーション等）を提供。
    - 設定取得ヘルパー _require による必須環境変数チェックを実装。

- ポートフォリオ構築
  - portfolio_builder.py:
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等分にフォールバック & 警告）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックを追加。既存保有のセクター別時価を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外ルールを適用しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティを追加。未知レジームは警告のうえ 1.0 でフォールバック。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
      - risk_based: 許容リスク率・損切り幅から基本株数を算出。
      - equal/score: weight に基づく配分と per-position 上限・aggregate cap のスケーリング、単元株（lot_size）丸め、cost_buffer を加味した保守的な投資見積を実装。
      - aggregate cap 超過時はスケールダウン後、端数（lot 単位）の追加配分ロジックで残余キャッシュを反映。
      - 価格欠損時のスキップやデバッグログを考慮。

- 研究（Research）
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を利用してモメンタム・ボラティリティ・バリュー系ファクターを計算する関数群を実装。移動平均や ATR 等の窓計算はウィンドウ関数で実装。
    - データ不足時に None を返す設計、スキャン範囲にカレンダーバッファを取る実装。
  - research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得するクエリを実装（ホライズンの検証と最大スキャン範囲の制限あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と、count/mean/std/min/max/median の統計要約を提供。
  - research パッケージに zscore_normalize（kabusys.data.stats 由来）などを __all__ でエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを算出し、ai_scores テーブルへ書き込む処理を実装（スコアは ±1.0 にクリップ）。
    - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策（記事数・文字数上限）、リトライ（429/ネットワーク/5xx に対する指数バックスオフ）やレスポンスの厳密な JSON バリデーションを導入。
    - タイムウィンドウ（JST ベース -> UTC 変換）計算ユーティリティ calc_news_window を実装。
    - API キーの解決（引数 > 環境変数）と未設定時の ValueError を追加。
    - （注）ファイルは末尾で一部切れているが、設計・安全策が明確に記載されている。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。SQLite（デフォルト: data/paper_trading.db）からシステム安定性・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を集計して標準出力にレポート出力。
    - P95 の計算、日付フィルタの WHERE 文生成、欠損テーブルに対する安全なフォールバック処理、判定基準（稼働率・成功率等の閾値）を導入。
    - CLI 引数（--from, --to, --db）をサポート。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows と POSIX 系の差分を吸収）。
    - set_cpu_affinity でカレントプロセスを最初の N コアに固定する機能を追加。
    - 権限不足や未対応機能発生時に警告ログを出す fail-safe を実装。

### Changed
- 環境変数の自動ロード順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local は上書き可能。
- run_monitoring は監視用途の DB に本番 sqlite_path を常に使用するように設計（環境に依存せず監視データは一元化）。
- position_sizing の aggregate cap ロジックで cost_buffer を導入し、コスト見積りを保守的に行うように変更。
- portfolio/risk_adjustment: "unknown" セクターの扱いを明示（上限適用除外）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを改善し、誤った .env の解析を減らす。
- 設定取得時の不正値に対する明確なエラーメッセージ（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
- process_priority・set_cpu_affinity での例外（AccessDenied/NotImplemented など）を捕捉し、アプリケーションを停止させないように改善。
- report ツールでの P95 計算や NULL 値ハンドリングを改善し、データ欠損時に N/A を返すようにした。

### Security
- OpenAI API キーは引数または環境変数で渡す設計とし、未設定時は ValueError を出して誤動作を防止。

### Notes / Known limitations
- ai/news_nlp.py はファイル末尾が切れている（実装途中の可能性あり）。実運用前に完全な処理（API 呼び出し部・DB 書き換え部）の検証が必要。
- position_sizing の価格欠損時に前日終値等へのフォールバックは未実装（TODO コメントあり）。
- 単元株（lot_size）は現時点でグローバル固定（デフォルト 100）。将来的に銘柄別 lot_map への対応を想定。
- DuckDB を用いる研究モジュールは prices_daily/raw_financials 等のテーブルスキーマに依存。DB データ品質により結果が変動するため前処理に注意が必要。

---

参考:
- README やドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照することで各関数の設計背景・根拠を確認できる旨をコード内にコメントで明示しています。
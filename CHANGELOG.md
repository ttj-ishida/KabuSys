Keep a Changelog — 変更履歴 (日本語)
※ 本ドキュメントはコードベースの内容から推測して作成しています。実際のリリース履歴と差分がある場合は適宜修正してください。

Unreleased
- 改善予定 / TODO
  - price の欠損時に前日終値や取得原価でフォールバックする仕組みの導入（portfolio/risk_adjustment.py の TODO）。
  - 銘柄ごとの単元（lot_size）をマスタで管理し、銘柄別 lot_map を受けられるように拡張（position_sizing.py の TODO）。
  - DuckDB の executemany に関する制約を踏まえた安全なバルク書き込みの改善（ai/news_nlp.py の実装注記）。
  - OpenAI 呼び出しの部分で部分失敗時の耐障害性向上（部分書き込みの保護など）。
  - モニタリングのポーリング失敗時メトリクスの詳細化や通知連携強化。

0.1.0 — 2026-04-13
Added
- 起動スクリプト / 実行フロー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - BrokerClientFactory を用いたブローカークライアント生成（環境に応じて Mock を使用して paper_trading と本番を分離）。
    - ExecutionEngine の起動前にプロセス優先度を High に設定（utils/process_priority.set_process_priority）。
    - Paper Trading 環境では専用 SQLite（data/paper_trading.db デフォルト）を使用する仕組みを導入。
    - RiskManager / OrderManager / Reconciler 等の組立てとデフォルト RiskConfig を定義。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB を確実に参照）。

- 設定・環境変数
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml による）による .env / .env.local 自動ロード。
    - .env 解析の強化（export プレフィックス対応、クォート内エスケープ、インラインコメント処理等）。
    - 必須環境変数チェック（_require）と各種プロパティ（DB パス、PID ファイル、しきい値等）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH サポート。

- ポートフォリオ構成
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分・スコア重み（calc_equal_weights / calc_score_weights）を実装。
    - スコア全て 0 の場合は等配分にフォールバックし WARNING を出力。

  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算ロジックを実装。
    - 単元株（lot_size）丸め、max_position_pct・max_utilization に基づく上限、コストバッファを考慮した aggregate cap スケーリング。
    - risk_based 方式では risk_pct / stop_loss_pct に基づくリスクベース sizing。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有を考慮して同一セクターの新規候補を除外。
    - 市場レジーム乗数（calc_regime_multiplier）：bull/neutral/bear に応じた乗数（デフォルトマップ）。未知レジームはフォールバック。

- リサーチ／ファクター計算
  - research/factor_research.py
    - Momentum / Volatility / Value に関するファクター計算関数を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe などを計算。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ランク化ユーティリティ rank、ファクター統計 summary を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。

  - research パッケージ __all__ に主要関数をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_scores を作成・書き込み。
    - バッチサイズ、最大記事数・文字数トリム、エクスポネンシャルバックオフによるリトライ、429/ネットワーク/5xx 対応のリトライ戦略を実装。
    - 入力/出力の厳格な JSON バリデーション、スコアを ±1.0 にクリップ。
    - API キー未設定時は明示的なエラーを送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI）。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL を判定する閾値を定義。
    - 日付フィルタ（--from / --to）・DB パス指定 (--db / 環境変数) に対応。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows 用の HIGH_PRIORITY_CLASS と POSIX の nice 値の差分を吸収）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）。
    - 権限不足や未対応 OS 時には警告を出して安全にスキップ。

Changed
- 監視と実行の DB 扱いを明確化
  - 監視 (run_monitoring) は常に本番 sqlite_path を参照するよう明示（監視データは本番 DB を使用）。
  - 実行 (run_execution) は paper_trading 環境時に専用 SQLite を使用して本番 DB と完全分離。

Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export キーワード対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの正しい扱い等を実装し、実運用での .env 設定ミスを低減。

- 初期化の冪等性
  - init_monitoring_db を呼ぶことで監視テーブルの存在を保証（何度呼んでも安全）。

Security
- API キーと必須環境変数の明示的チェック
  - OpenAI API キー未設定時に ValueError を投げる（ai/news_nlp.py）。
  - 必須トークン等は Settings 経由で _require により存在を検証。

Notes / 実装上の留意点
- DuckDB / SQLite を組み合わせて分析・監視・実行を分離しているため、分析クエリは DuckDB に集約され高速に実行可能。
- 多くの関数は純粋関数設計（DB 参照なしの処理はメモリ上完結）でテストしやすい実装。
- ロギングは INFO レベルを基本に使用。予期せぬ例外は logger.exception によって記録しつつループ継続する設計（監視ループ等）。

脚注
- 本 CHANGELOG はコードコメントや実装内容から推測して作成しています。実際のリリースポリシーやバージョン管理の履歴がある場合は公式履歴に合わせて更新してください。
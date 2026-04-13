CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本パッケージ初版を追加（バージョン 0.1.0）。
- 起動スクリプト / 実行関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - DuckDB 接続を併用、監視用 DB の初期化を行う（init_monitoring_db）。
    - プロセス優先度を最初に "high" に設定する処理を追加（set_process_priority を利用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - 環境変数自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
    - .env パーサ実装: export プレフィックス、クォート文字列、インラインコメント、エスケープシーケンス等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - Settings クラスを追加し、各種設定（API トークン、DB パス、PID / kill flag パス、閾値、環境判定 etc.）をプロパティで提供。値検証（許容値チェック）を行う。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルトを提供。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート/候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア全0 の場合は等金額にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装（既存ポジションのセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull:1.0 / neutral:0.7 / bear:0.3、未知のレジームは警告して1.0でフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じた (risk_based / equal / score) 処理、単元株丸め（lot_size）、1銘柄上限・aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を使った保守的見積り、残差処理によるロット単位での追加配分をサポート。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を追加し、Windows と POSIX（Linux/Mac/FreeBSD）で差異を吸収してプロセス優先度を設定。失敗時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) を追加（最初の N コアに固定）。引数検証・失敗時のフォールバック動作あり。
- リサーチ/特徴量
  - research/factor_research.py
    - モメンタム（1/3/6ヶ月）、200日移動平均乖離、ATR20、平均売買代金、ボラティリティ等のファクター計算を DuckDB 上の prices_daily / raw_financials を参照して実装。
    - データ不足時の None ハンドリング、ウィンドウ計算のバッファ設計を反映。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman）計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない純 Python 実装。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を使って銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) を用いてセンチメントスコア（-1.0〜1.0）を生成して ai_scores に書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数のトリム（最大記事数/最大文字数）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分成功に備えた安全な DB 更新（対象コードのみ置換）を設計。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。
    - 特定の実装ノート（DuckDB の executemany 制約やルックアヘッドバイアス回避のため datetime.today() を参照しない等）をコードに明示。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して Pass/Fail 判定する。デフォルト閾値を定義（稼働率 99%、成立率 90% 等）。
    - 日付フィルタ、DB 存在チェック、各テーブル（system_status / trade_logs / risk_logs） が存在しない場合の耐性を持つ。
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - research パッケージの __all__ を整理して主要 API を公開。
  - portfolio パッケージの __all__ を整理して公開関数をエクスポート。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Deprecated
- 該当なし。

Security
- OpenAI API キー等の必須シークレットは明示的に要求し、未設定時はエラーを発生させることで意図しない挙動を防止。

Notes / Implementation details
- DB: SQLite（monitoring.db / paper_trading.db）および DuckDB（kabusys.duckdb）を併用する設計。
- 環境設定: .env 自動読み込みはプロジェクトルート検出（.git / pyproject.toml）に基づく。OS 環境変数は保護され、自動ロードは環境変数で無効化可能。
- ポートフォリオ / リスク / サイジングの実装は設計ドキュメント（PortfolioConstruction.md, StrategyModel.md, 等）に準拠した純関数群として提供され、状態を持たないためユニットテストしやすい。
- プロセス優先度や CPU affinity の設定は権限やプラットフォーム制約で失敗する可能性があるため、失敗時にログ出力して処理を継続するようにしている。

Acknowledgements
- 本リリースは初期機能セットの導入を目的としたものであり、将来的な改善（価格フォールバック、銘柄別 lot_size 管理、より堅牢なエラーハンドリング等）を予定しています。
# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
慣例に従いセマンティックバージョニングを想定しています。

## [Unreleased]

- ドキュメント・TODO の整理、細かな内部改善を予定。
- 一部のエラーケースやフォールバック挙動の追加検討（ログ・監視強化など）。

## [0.1.0] - 2026-04-12

初回リリース。主要機能とユーティリティ群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）。
    - 監視は常に本番 sqlite_path を使用して DB を初期化（init_monitoring_db）。
    - DuckDB 接続を併用。
    - プロセス優先度を設定（utils.process_priority.set_process_priority）。
    - SIGINT (KeyboardInterrupt) で正常終了し、DB コネクションをクローズ。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine を実行。
    - DuckDB を分析用に併用。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。
    - .env パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
    - 環境値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
    - 各種パス・閾値のプロパティ化（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path 等）。
    - settings インスタンスをエクスポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 選定。
    - calc_equal_weights, calc_score_weights: 重み計算（score が全て 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの集中上限チェック（既存ポジションを考慮）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・現保有・価格等から発注株数を計算。
    - risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（利用可能現金）に応じたスケーリングと残差処理を実装。
    - cost_buffer による手数料・スリッページの見積り考慮。

- 研究・ファクター
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB を利用して prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ATR、流動性、PER/ROE を計算。
  - research/feature_exploration.py
    - calc_forward_returns: 各ホライズンの将来リターンを取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank, factor_summary: ランキング変換と統計サマリー機能。
  - research パッケージは zscore_normalize（data.stats から）をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、UTC 変換）機能を提供（calc_news_window）。
    - 最大記事数 / 文字数トリム、銘柄単位で最大バッチサイズ (_BATCH_SIZE=20) のバッチ化処理。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ戦略（上限あり）。
    - レスポンスのバリデーション・スコアクリップ・部分成功時のデータ置換ロジック（既存スコア保護）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して標準出力にレポート出力。
    - コマンドライン引数で期間指定可能（--from, --to, --db）。
    - P95 算出、欠損時の N/A 表示や SQL が存在しない場合のフェイルセーフハンドリングを実装。

- ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX (Linux/macOS/FreeBSD) を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS を考慮したフォールバック / 警告ログを実装。

### Changed
- 全体
  - DuckDB を分析用途として幅広く導入（research / ai / 実行エンジンの分析用接続）。
  - paper_trading 環境では DB を本番と分離する運用方針を採用（安全性向上）。
  - 多くの関数で入力検証とログ出力を強化し、フェイルセーフに配慮。

### Fixed
- 環境変数パーシング
  - .env の quoted 値とエスケープシーケンス、export プレフィックス、インラインコメントの扱いを改善。
- モニタリングポーリング間隔
  - MONITOR_POLL_INTERVAL に不正（0 以下・非整数）が設定された場合にデフォルトへフォールバックして例外発生を回避。警告ログを出力。
- プロセス優先度設定の例外処理
  - psutil による権限不足や未実装機能での例外をキャッチし、処理をスキップしてログに警告するように。

### Notes / Known issues
- ai/news_nlp.py の処理は外部 API（OpenAI）依存のため、API キーやレート制限、レスポンスフォーマットの変化に注意が必要。スキーマ検証を導入しているが追加の堅牢化を検討中。
- position_sizing の価格欠損時（price == 0.0）はエクスポージャーや算出の過少評価を招く旨の注記あり。将来的に前日終値等のフォールバックを検討。
- DuckDB の executemany の挙動に対する防御（空パラメータ防止等）が必要な箇所あり（コメントあり）。
- 一部の関数は大量データを扱う設計のため、パフォーマンスチューニング（インデックス、クエリ最適化）が今後の課題。

---

これらの変更点はコードベースから推測してまとめたものであり、実際のコミット履歴やリリースノートと完全一致しない場合があります。必要であれば、各ファイルや関数ごとの詳細な変更点（行レベル）を追加で生成します。
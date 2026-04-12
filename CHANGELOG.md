CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
セマンティックバージョニングに従います（https://semver.org/）。

[0.1.0] - 2026-04-12
--------------------

Added
- 初回公開: KabuSys パッケージ（日本株自動売買システム）の初期実装を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 設定管理:
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - 行単位パーサの実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮。
    - Settings クラスを導入し、環境変数の取得・バリデーションを集中管理（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。
    - デフォルト値およびパス補完（expanduser）をサポート: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など。
- 実行用エントリスクリプト:
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトへフォールバックして警告出力。
    - 起動時にプロセス優先度を "high" に設定（utils の set_process_priority を使用）。
    - 監視データベースは環境にかかわらず本番 sqlite_path を使用する挙動。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して完全に分離。
    - BrokerClientFactory を使ったブローカークライアントの切替、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ:
  - init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。
- ユーティリティ:
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS、POSIX: nice 値）。
    - CPU affinity 固定ユーティリティ set_cpu_affinity（最初の N コアに固定）。
    - 権限不足や未対応 OS に対しては警告を出してスキップするフェイルセーフ。
- ポートフォリオ構築（純粋関数群、DB 参照なし）:
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順（タイブレークに signal_rank）で候補抽出。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全0 の場合は等金額へフォールバックし警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有時価を用いて、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックと警告）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り、余剰キャッシュを使った端数配分ロジックを実装。
- 研究（Research）モジュール:
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを利用してファクターを計算（MA200、ATR20、リターン等）。
    - スキャン期間のバッファ取りや欠損値の扱いを明示。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。ホライズン検証（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（IC）を実装。レコード不足や定数分散の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）や統計サマリー（count/mean/std/min/max/median）を提供。ties の取扱いと丸めで再現性を確保。
  - research パッケージの公開インターフェイスを整備（zscore_normalize を含む）。
- AI ニュース NLP:
  - src/kabusys/ai/news_nlp.py（ニュースセンチメントスコアリング）
    - ニュース集約ウィンドウ計算（JST→UTC 変換）、記事トリム（最大記事数・文字数）、OpenAI（gpt-4o-mini）へのバッチ送信、JSON Mode の厳格検証、スコアクリッピング（±1.0）、エクスポネンシャルバックオフによる再試行方針、部分成功時のテーブル書換戦略（DELETE → INSERT の限定的置換）などを実装。
    - API キー解決ロジック（引数優先、環境変数 OPENAI_API_KEY をフォールバック）。
- ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成コマンドラインツールを追加。
    - 期間指定 (--from / --to)、DB パス指定 (--db) をサポート。PAPER_TRADING_SQLITE_PATH 環境変数とデフォルトパスを考慮。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL 判定を出力。閾値はファイル内定数で管理（例: 稼働率 >= 99%、P95 <= 200 ms など）。
- パッケージ公開:
  - src/kabusys/portfolio/__init__.py、src/kabusys/research/__init__.py による公開 API 整備。

Fixed / Improved / Design decisions
- .env パーサの堅牢化:
  - クォート内エスケープ、インラインコメントの扱い、export プレフィックス対応などを実装し、実運用での .env 設定ミス耐性を向上。
- 環境変数のバリデーション:
  - MONITOR_POLL_INTERVAL の不正値や PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の不正値に対して明確なエラーメッセージやフォールバックを用意。
- DB 分離:
  - Paper Trading 実行時に本番 DB と完全分離する設計（paper_sqlite_path を使用）を明確化し、安全性を確保。
- フェイルセーフの強化:
  - process_priority / set_cpu_affinity で権限不足や未対応プラットフォームを検出した場合、例外化せず警告して継続する挙動に統一。
  - AI スコアリングで API を利用できない場合は早期にわかるエラーを出し、部分失敗時でも既存データ保護の設計（対象コード絞った置換）を採用。
- 計算関数は基本的に純粋関数（副作用なし、DB 参照箇所は明示）に分離する設計を採用。これにより単体テストやリサーチでの再利用性を高める。

Known issues / Notes
- news_nlp.py の一部処理の説明（ファイル末尾）に途中で切れたコメントが残っている可能性があります。実装自体は主要な設計を含みますが、運用上の細かな振る舞い（部分失敗時の DB 書換やログの詳細）が調整を要する場合があります。
- position_sizing の price フォールバックについて TODO コメントあり（price が欠損時の過少見積り問題）。将来的に前日終値や取得原価でのフォールバックを検討予定。
- calc_score_weights はすべてのスコアが 0.0 の場合に等金額配分へフォールバックし警告を出力する仕様です（予期しない重み分布を避けるため）。

Security
- 初期実装のため機密情報管理は環境変数経由を想定。OPENAI_API_KEY 等の取り扱いは環境変数で行い、.env ファイルはローカル専用（.env.local を想定）での使用を推奨。

Closed / Removed
- 該当なし（初回リリース）。

----------

今後の予定
- 単体テストの追加（ファクター計算・ポジションサイズ・AI スコアリングのモックテスト等）。
- エラー計測・アラート（監視のアラート連携、LINE Messaging API の活用）。
- price フォールバックや銘柄別 lot_size のサポートなど、一部 TODO の解消。

（以上）
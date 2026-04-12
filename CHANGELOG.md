CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
履歴は逆順（新しいリリースを上）に記載します。

Unreleased
----------

（現在のコードベースは 0.1.0 の初版リリース相当のため、Unreleased セクションは空です。）

0.1.0 - 2026-04-12
------------------

Added
- パッケージ初版リリース。
  - バージョン: kabusys.__version__ = "0.1.0"

- 実行エントリ & 実行基盤
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。BrokerClientFactory を用いて環境（本番/ペーパー）に応じたブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててセッションを実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非数）の場合は警告を出してデフォルトにフォールバック。
    - 監視（monitoring）部分は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化・更新。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを堅牢化（export 句、クォート内のエスケープ、インラインコメントルール等に対応）。
    - Settings クラスを追加し、各種環境変数をプロパティで提供:
      - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
      - PAPER_FILL_MODE の検証（instant/partial/never/reject の許容、無効値は例外）
      - PID ファイル / kill flag 関連設定
      - CPU/MEM/DISK の閾値（デフォルト値をプロパティで取得）
      - KABUSYS_ENV（development / paper_trading / live）の検証
      - LOG_LEVEL の検証

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）と制限。
    - calc_equal_weights, calc_score_weights: 等配分・スコア重み配分。全銘柄スコアが 0 の場合は等金額配分へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター集中を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告とともに 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各 allocation_method に対応した株数計算を実装。
      - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差に対する再配分ロジックを実装。
      - 価格欠損やマイナス値に対する安全弁（スキップ・ログ出力）を実装。

- 監視・ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（psutil 使用）。権限不足等は警告にフォールバック。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留め。引数検証と例外ハンドリングあり。

- 解析・リサーチ
  - research/factor_research.py
    - DuckDB を用いたファクター計算を実装（モメンタム、ボラティリティ、バリュー）。
    - calc_momentum, calc_volatility, calc_value を提供し、prices_daily / raw_financials テーブルのみ参照する設計。
    - 長期移動平均（MA200）、ATR、平均出来高などを計算。データ不足時には None を返す。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターンを複数ホライズンで一括取得（SQL LEAD を利用）。
    - calc_ic: Spearman ランク相関（IC）計算（ties の平均ランク処理を含む）。有効レコードが 3 未満のときは None を返す。
    - factor_summary, rank: 基本統計量とランク関数（pandas 等外部依存なし）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI API（デフォルトモデル gpt-4o-mini）へバッチで送信してセンチメントスコア（-1.0〜1.0）を算出。
    - 機能:
      - ニュース時間ウィンドウ計算（JST ベースを UTC に変換）
      - 1 回の API 呼び出しで最大 20 銘柄まで処理、記事・文字数の上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ
      - レスポンス検証 (JSON 構造・型・既知コード・数値型) とスコアの ±1.0 クリップ
      - 部分成功時でも既存スコアを保護するため、影響のあるコードのみ置換（DELETE → INSERT の手順）
    - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - 実装はフェイルセーフ指向（API 失敗時はスキップして継続）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成 CLI を追加。
    - SQLite（paper_trading DB）から集計して次の指標を出力:
      - 稼働率（system_status）、総ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ（平均・最大・P95）
    - PASS/FAIL 判定基準を定義（閾値: uptime>=99%, fill_rate>=90%, send_rate>=95%, P95_latency<=200ms 等）。
    - コマンドライン引数で期間（--from / --to）と DB パス（--db）を指定可能。

Changed
- パッケージのエクスポートを整理
  - portfolio, research モジュール等の __all__ を整備し、主要 API をトップレベルからインポート可能に。

Fixed
- （初版のため既知のバグ修正履歴はなし。コード内に将来の改善点・TODO コメントあり。）

Deprecated
- なし

Removed
- なし

Security
- AI モジュール・外部 API 周りは API キーの未設定チェックやレスポンス検証を行い、誤ったデータ流入や未設定によるクラッシュを防止する措置を実装。

Notes / 既知の制約・今後の改善点
- position_sizing の価格欠損時（price == 0.0）の扱い: 現状はスキップし、将来的には前日終値や取得原価をフォールバックする案をコメントとして残している。
- apply_sector_cap は "unknown" セクターに対しては制限を適用しない実装。ただしマスタ欠損時に過少見積りされる可能性があることがコメントで示されている。
- ai/news_nlp の一部実装（ファイル末尾）が切れている点に注意。完全なロジック（リトライ実装、DB 書き込み詳細など）は実装済みである旨のコメントが存在するが、運用時に追加検証が必要。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール環境で動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定し、明示的に環境変数を与えることを推奨。

お問い合わせ
- 本 CHANGELOG の内容はリポジトリ内のソースコードから推測して作成しています。実運用・リリースノート作成時には実際のコミット履歴・バージョン管理ログを参照して確定してください。
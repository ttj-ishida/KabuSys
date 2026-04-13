Keep a Changelog
=================

すべての注目すべき変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

リリース日: 2026-04-13

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初回リリース。パッケージ kabusys の基本コンポーネントを実装。
  - パッケージバージョンは __version__ = "0.1.0"。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH 默認: data/paper_trading.db）を使用して本番DBと完全分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - Broker クライアントは BrokerClientFactory 経由で生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を実行。
    - 監視用テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値や 0 以下はデフォルトにフォールバックし、警告を出力。
    - 監視処理は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計（監視 DB を本番側で一元管理する意図）。

- 設定管理
  - config.py
    - .env 自動ローディング実装 (.env, .env.local 順)。プロジェクトルートの検出は .git または pyproject.toml を基準に行うため CWD に依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - .env パーサは export KEY=val 形式、クォート/エスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種設定プロパティを型変換・バリデーション付きで取得可能（例: env, log_level, PAPER_FILL_MODE の有効値チェックなど）。
    - データベースパス（duckdb, sqlite, paper_trading sqlite）、監視関連パス（pid_file, kill_flag）や閾値（CPU/MEM/DISK）等をプロパティで提供。

- ポートフォリオ構築（メモリ内純粋関数群）
  - portfolio.portfolio_builder
    - BUY シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全銘柄スコアが 0 の場合は等金額にフォールバックして WARNING を出力。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を検出して新規候補から除外するロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出し 1.0 でフォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）を実装。
    - cost_buffer を考慮した保守的コスト見積り、スケールダウン時の残差配分ロジックを実装。

- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value の実装。
    - prices_daily / raw_financials を参照して、モメンタム（1M/3M/6M, MA200乖離）、ATR、平均売買代金、PER/ROE 等を計算。
    - データ不足時は None を返し、結果は (date, code) ベースの dict リストを返却。

  - research.feature_exploration
    - calc_forward_returns: 目標日から将来リターン（複数ホライズン）を計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - factor_summary: count/mean/std/min/max/median の基本統計量を算出。
    - rank: 同順位は平均ランクとする処理（round(..., 12) による丸めで ties 検出の安定化）。

  - research.__init__ で zscore_normalize（data.stats から）をエクスポート。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ: target_date に対して JST 基準で前日 15:00 〜 当日 08:30（内部は UTC に変換）。
    - バッチサイズ、記事数・文字数トリム、最大リトライ（429/ネットワーク/5xx 共通、指数バックオフ）等の実装。
    - レスポンス検証、スコア ±1.0 クリップ、部分書き換え方式（対象コードのみ DELETE→INSERT）で ai_scores を更新し、部分失敗時に既存データ保護。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート表示。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db コマンドライン引数に対応。DB ファイルが存在しない場合のエラーメッセージを出力。

- ユーティリティ
  - utils.process_priority
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（アクセス権限がない場合は警告でスキップ）。

Changed
- 監視の挙動に関する設計注記
  - run_monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用する点を明確化（監視データは本番側に集約する想定）。
- 環境変数ロード
  - .env の読み込み順序は OS 環境変数 > .env.local > .env。OS 環境変数は protected として .env/.env.local による上書きを防ぐ。

Fixed
- （初回リリースのため過去のバグ修正履歴はなし）

Notes / Implementation details
- DuckDB を集計・リサーチ用途に利用しており、prices_daily / raw_financials / raw_news などのテーブルを想定。
- 外部依存: psutil（プロセス操作）、duckdb、openai（OpenAI Python クライアント）。これらの環境での動作確認が必要。
- すべての研究・ポートフォリオ計算関数は DB 参照が限定的（research は DuckDB のみ、portfolio はメモリ内純関数）で、取引系の実行ロジックとは明確に分離している設計。
- CLI スクリプト（run_execution, run_monitoring, tools.paper_verification_report）は __main__ エントリを持ち、直接実行可能。

Security
- OpenAI API キーは環境変数により設定可能。キーが未設定のまま操作しないよう ValueError を送出する設計。

今後の予定（短期ロードマップ）
- logging レベル設定を Settings.log_level を基に反映
- position_sizing の lot_size を銘柄別で扱う拡張（stocks マスタとの連携）
- news_nlp のレスポンススキーマ検証強化と部分リトライの改善
- テストカバレッジ拡充（特に DuckDB クエリ部分と OpenAI 周りのフェイルセーフ）

---

この CHANGELOG はコードベースから推測して作成したもので、実際のコミット履歴に基づくものではありません。必要に応じて日付や範囲、項目の追加・修正を行ってください。
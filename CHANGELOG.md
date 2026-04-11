# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。時間順に新しいリリースを上に記載します。

## [0.1.0] - 2026-04-11

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装。
- 実行・監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。起動時にプロセス優先度を "high" に設定。
    - 環境変数 KABUSYS_ENV により paper_trading モードを切替可能（paper_trading 時は MockBrokerClient を利用し、専用 SQLite（デフォルト data/paper_trading.db）へ記録して本番 DB と分離）。
    - duckdb（デフォルト data/kabusys.duckdb）と SQLite を併用。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視系は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理モジュールを追加（config.py）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パースの実装（コメント、export プレフィックス、クォート／エスケープに対応）。
  - 多数の設定プロパティを提供（J-Quants / kabu / LINE / DB パス / paper_trading 用設定 / 監視閾値 / PID ファイル等）。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。

- ポートフォリオ構築モジュール（kabusys.portfolio）を追加
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 件の選定（スコア降順、タイブレーク: signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"/"neutral"/"bear" をマッピング、未知レジームは 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）を適用。コストバッファ（cost_buffer）を考慮したスケーリングや残余配分ロジックを実装。

- 研究系モジュール（kabusys.research）を追加
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算（DuckDB SQL を利用）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: raw_financials を用いた PER / ROE 計算（target_date 以前の最新レコードを使用）。
    - 計算は DuckDB の prices_daily / raw_financials テーブルを参照し、ルックアヘッド対策・ウィンドウチェックを実施。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括 SQL で取得。ホライズンの検証（1–252）を実施。
    - calc_ic, rank: スピアマンランク相関（IC）計算、ランク付けユーティリティ（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

- AI 系モジュール（kabusys.ai）を追加
  - news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む。
    - 処理の主要特徴:
      - タイムウィンドウ計算（target_date に基づく JST→UTC 変換）を分離した calc_news_window を提供。
      - 1 銘柄あたり記事数／文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
      - バッチ送信（最大 20 銘柄）と JSON mode の利用、レスポンス検証、スコアを ±1.0 にクリップ。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - DuckDB への書き込みはトランザクションで冪等に実行（対象コードのみ DELETE → INSERT）。
      - OpenAI 呼び出し部分は _call_openai_api で分離され、テスト時に差し替え可能。
  - regime_detector.py
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定して market_regime テーブルへ冪等書き込みを行う。
    - マクロ記事はキーワードフィルタリングで抽出し、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフを適用。

- ユーティリティ群を追加（kabusys.utils）
  - process_priority.py
    - psutil を利用して OS 間の差を吸収したプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）と CPU affinity 設定を提供。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- パッケージ初期化
  - __version__ = "0.1.0"
  - package __all__ の整理（portfolio / research / ai 等のエクスポート）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

### Notes / 注意事項
- 環境変数およびデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings 経由で取得可能。
- .env の自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行われる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。無効値（0, 負数, 非数）の場合はデフォルト 60 秒にフォールバックし、警告ログを出力する。
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を必要とする。未設定時は明示的にエラーを投げるか、モジュール内でフェイルセーフ（macro_sentiment=0.0 など）を採用している箇所があるため、挙動に注意。
- DuckDB への executemany は空リストを渡せない制約（DuckDB 0.10 を想定）に対する保護ロジックを実装している。
- AI 出力は JSON を期待するが、余分なテキスト混入に備え最外の {} を抽出して復元する処理を行う（それでもパースに失敗した場合は当該チャンクをスキップする）。
- process_priority / cpu_affinity は権限によって失敗する可能性があり、その場合はワーニングを出して処理を継続する設計。

---

今後のリリースでは、ユニットテスト、ドキュメントの充実（API 使用例、DB スキーマの説明）、銘柄ごとの lot_size マスタ対応、エラーハンドリングのさらなる堅牢化を予定しています。
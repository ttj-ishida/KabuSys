CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

（現状なし）

0.1.0 - 初回公開
----------------

リリース日: 未設定

Added
- 基本パッケージ導入
  - パッケージバージョンを 0.1.0 として公開。
  - パッケージ説明文字列の追加（src/kabusys/__init__.py）。

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッション実行。
    - duckdb（デフォルト data/kabusys.duckdb）を参照。
    - 監視テーブルの存在を保証する init_monitoring_db を起動前に呼び出す（冪等）。
    - RiskManager のデフォルト設定（最大ポジション比・利用率・レート制限・サーキットブレーカー等）を実装。initial_portfolio_value は broker.get_available_cash() で取得。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非数値）はデフォルトにフォールバックして警告ログを出力。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path（Settings.sqlite_path、デフォルト data/monitoring.db）を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB への接続を確立して SystemMonitor.check_once() を定期実行。例外はログ記録してループ継続（フェイルセーフ）。

- 設定管理
  - config.py: 環境変数 / .env 自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env → .env.local の順に読み込む（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env パーサ実装: export プレフィックス、クォート（シングル／ダブル）内のエスケープ、インラインコメントの扱いなどをサポート。
    - Settings クラスを提供。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須キー取得（未設定時は ValueError）。
      - KABUSYS_ENV（development / paper_trading / live）の検証。
      - PAPER_FILL_MODE（instant/partial/never/reject）の検証。
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や PID / KILL フラグパス。
      - 監視閾値（CPU/MEMORY/DISK）などのデフォルト値。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を追加（"high"/"normal"/"low"）。Windows と POSIX（Linux, Darwin, FreeBSD）を吸収。
    - set_cpu_affinity(cpu_count) を追加（指定が None の場合は無効）。
    - 権限不足や未対応 OS の場合は警告ログを出して処理をスキップするフェイルセーフを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順にソート、同点は signal_rank でブレークして上位 N を返す。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等配分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を既存保有に基づき判定し、上限を超えるセクターの新規候補を除外する。unknown セクターは適用除外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知値は 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
    - リスクベース: risk_pct, stop_loss_pct を用いた目標株数計算、単元株（lot_size）で丸め。
    - equal/score: weight に基づき per-position / aggregate cap を計算。
    - aggregate cap 超過時はスケーリングして lot_size 単位の再配分（端数処理を remainder による安定配分）を実装。
    - cost_buffer による保守的なコスト見積りをサポート。
    - price 欠損・0 値はスキップし、安全に動作するように設計。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB SQL を使用、ウィンドウ関数）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、ボリューム比等を計算。データ欠損時は None を返す設計。
    - calc_value: raw_financials から最新の財務データを取り出し PER, ROE を計算。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で算出。入力検証（1〜252）あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）をランク法で計算。3 件未満は None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量の集計（count/mean/std/min/max/median）。
  - research/__init__.py で主要 API をエクスポート（zscore_normalize を含む）。

- AI 関連機能
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 1 API コールで最大 20 銘柄（_BATCH_SIZE）を処理。JSON mode を利用して厳密な JSON レスポンスを期待。
    - リトライロジック: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ（上限回数あり）。その他のエラーはスキップして継続。
    - レスポンスのバリデーション: JSON パース、results リスト形式、各要素の code/score 検証、未知コードは無視、スコアは ±1.0 にクリップ。
    - 書き込みは冪等的に実行（BEGIN/DELETE/INSERT/COMMIT）。部分失敗で既存スコアを消さないよう、書き込むコードを絞って DELETE → INSERT。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

  - ai/regime_detector.py:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime（日次）を判定する機能を実装。
    - prices_daily のデータは target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュース抽出はタイトルにマクロキーワードを含む記事を対象（最大件数制限）。
    - OpenAI 呼び出しは失敗時に macro_sentiment = 0.0（中立）として継続するフェイルセーフ。
    - 合成スコアをクリップして閾値に基づき 'bull' / 'neutral' / 'bear' を決定。結果は market_regime テーブルへ冪等書き込み。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）
- ただし多数のフェイルセーフやバリデーション（環境変数検証、API レスポンス検証、データ欠損時のフォールバック等）を実装して堅牢性を高めています。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡す設計。コード内にハードコードはなし。
- .env 読み込みは OS 環境変数を保護する実装（.env.local でも上書きは OS 環境変数を上書きしない）。

Notes / Migration / Usage
- 環境変数とファイル
  - 自動 .env ロードはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - .env/.env.local の読み込み順: OS env > .env.local（上書き） > .env（未設定のみ）。
  - デフォルト DB パス: DuckDB: data/kabusys.duckdb, SQLite monitoring DB: data/monitoring.db, paper trading DB: data/paper_trading.db。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を秒単位で設定可能。1 未満や非整数値は無視してデフォルト 60 秒を使用。

- 実行時
  - run_execution.py / run_monitoring.py はそれぞれ main() を提供。直接実行可能（if __name__ == "__main__"）。
  - 両スクリプトは起動時にプロセス優先度を "high" に設定しようと試みますが、権限不足や未対応 OS の場合は警告ログで継続します。

- AI 機能
  - OpenAI 呼び出しはネットワーク・API 側の一時障害に対しリトライとフォールバックを行うため、完全成功しない場合でもシステム全体の停止を招きません（スコアが取得できなかった銘柄はスキップされる可能性あり）。
  - レスポンスの JSON バリデーションが厳格なため、モデルの返却フォーマットに互換性が必要です（_SYSTEM_PROMPT にて厳密 JSON を要求）。

開発者向けメモ（実装上の重要点）
- DuckDB を SQL ウェアハウスとして活用。research / ai モジュールは DuckDB 接続を受け取って SQL + Python で計算します。
- ルックアヘッドバイアス対策として、time.today()/date.today() を直接参照せず、target_date を引数として受ける設計を多用。
- 多くの関数は外部副作用を持たない純粋関数設計（portfolio モジュールなど）として実装され、テストが容易です。
- 単元株（lot_size）や cost_buffer、max_utilization などのパラメータは将来の拡張を見据え引数で渡せる設計。

今後の予定（例）
- 銘柄ごとの lot_size を stocks マスタから取得する拡張（position_sizing の TODO）。
- AI 呼び出しのモック用フックや細かなログ改善。
- market_regime / ai_scores 等のテーブルスキーマに対するマイグレーション機能。

お問い合わせ
- バグや提案は issues にて報告してください。
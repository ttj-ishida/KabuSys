CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは "Keep a Changelog" の形式に準拠しています。
意味的バージョニング（SemVer）を使用します。

フォーマットと方針:
- 重要な変更のみを記載します（内部実装の細かい修正やコメントのみの変更は省略）。
- 日付はリリース日を示します。

Unreleased
----------

- なし（初回公開リリースに向けた状態）。

[0.1.0] - 2026-04-12
--------------------

Added
- パッケージ初回リリース (バージョン 0.1.0)。
- 基本アーキテクチャ、起動スクリプト、ユーティリティ、ポートフォリオ構築、リサーチ、AI ニュース NLP、Paper Trading 検証ツールを追加。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite DB を使用して本番 DB と完全分離して実行する挙動を実装。
      - ブローカークライアント生成（BrokerClientFactory）・OrderRepository・OrderManager・RiskManager・Reconciler を組み立て、ExecutionEngine.run_session() を実行。
      - プロセス優先度を set_process_priority("high") で設定。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔が上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データは共通 DB）。
      - プロセス優先度設定と DB 初期化（init_monitoring_db）を含む。
  - 設定管理
    - config.py
      - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
      - .env パーシングを独自実装（export 形式、クォート、インラインコメントの扱いなどに対応）。
      - Settings クラスを提供し、各種環境変数の取得とバリデーションを実装。
      - DB パス（DUCKDB_PATH、SQLITE_PATH）、paper trading 用 DB パス、PID / kill flag パス、閾値設定（CPU/MEM/DISK）などのプロパティを提供。
      - 環境 KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py
      - 選定関数 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
      - スコアが全て 0 の場合に等配分へフォールバックするロジックと警告ログを実装。
    - portfolio/risk_adjustment.py
      - apply_sector_cap によるセクター集中制限適用ロジックを追加（既存保有と当日売却予定を考慮）。
      - calc_regime_multiplier による市場レジーム（bull/neutral/bear）に基づく資金乗数を追加（未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - 複数手法（risk_based / equal / score）に対応した株数算出ロジックを実装。
      - 単元株丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、残差に対する lot_size 単位での追加配分アルゴリズムを実装。
      - cost_buffer による手数料/スリッページ見積りを考慮。
  - リサーチ / ファクタ計算
    - research/factor_research.py
      - momentum / volatility / value ファクター計算実装（DuckDB を利用、prices_daily / raw_financials テーブル参照）。
      - MOMENTUM, MA200, ATR, volume 等の計算を SQL ウィンドウ関数で効率的に取得。
    - research/feature_exploration.py
      - 将来リターン calc_forward_returns、IC（calc_ic）、ファクター統計要約 factor_summary、ランク変換 rank を実装。
      - 外部依存（pandas 等）無しで標準ライブラリのみで実装。
    - research パッケージは z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）を公開対象に含める設計。
  - AI ニュース NLP
    - ai/news_nlp.py
      - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI API（gpt-4o-mini、JSON Mode）でセンチメントを -1.0〜1.0 にスコア化して ai_scores に書き込む処理を実装。
      - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（1銘柄あたりの最大記事数・文字数制限）を実装。
      - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限回数あり）を実装。
      - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードを絞って DELETE→INSERT）を考慮。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を送出。
      - ニュース収集ウィンドウは JST ベース（前日 15:00 〜 当日 08:30）を UTC に変換して使用。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI を追加（期間指定 --from / --to、DB パスオプション --db）。
      - システム安定性（uptime）、注文成功率（fill/send rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力。
      - P95 計算、日付フィルタ、DB 存在チェック、テーブル欠損時のフォールバックを実装。
  - ユーティリティ
    - utils/process_priority.py
      - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 利用）。
      - CPU affinity 固定機能 set_cpu_affinity を実装。
      - 権限不足や未対応 OS では警告を出して安全にスキップする設計。
  - DB 連携
    - DuckDB をリサーチ・AI スコアリング向けの列指向分析 DB として利用（DUCKDB_PATH デフォルト data/kabusys.duckdb）。
    - SQLite をモニタリング／paper trading 用記録 DB として利用（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
    - init_monitoring_db による監視テーブル初期化が起動スクリプトで呼び出される（冪等性確保）。
  - パッケージ情報
    - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー等は環境変数経由で提供することを想定。未設定時は明示的な例外を発生させることで誤った公開や無効なアクセスを防止。

Notes / Known limitations
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。プロジェクトルートが検出できない場合は自動ロードをスキップする。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- paper_trading 環境は production DB と完全分離される設計。誤操作で本番 DB に混入しないよう意図された動作。
- position_sizing では現在 lot_size がグローバル固定（全銘柄共通）で、将来的に銘柄別 lot_map へ拡張予定（コード中に TODO コメントあり）。
- apply_sector_cap は price が欠損（0.0）だとエクスポージャーが過少推定されうる旨をコメントに記載している（将来のフォールバック価格戦略が未実装）。
- ai/news_nlp の実装は堅牢化（リトライ、検証、部分更新）を重視しているが、API 利用時のコスト・レート制限に注意する必要あり。
- DuckDB の executemany の制約（バージョン依存）を考慮した安全な実行が意識されている箇所あり（tools / ai で扱いに注意）。

開発者向けメモ
- ログレベルや閾値等は環境変数で変更可能（LOG_LEVEL、CPU_THRESHOLD_PCT 等）。
- 起動時にプロセス優先度を high に設定するため、実行環境での権限（Linux の nice 降下、Windows の権限）が必要な場合がある。
- OpenAI を利用する機能を使う場合は OPENAI_API_KEY を適切に設定すること。

ライセンス / 貢献
- 初回リリース。以降のリリースで貢献者・ライセンス情報を追記予定。

--- 

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴やバージョン管理情報があれば、それに基づく正確な履歴に差し替えることを推奨します。
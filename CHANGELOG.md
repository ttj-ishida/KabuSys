CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）に整理しています。
- バージョンは [version] - YYYY-MM-DD の形式で記載しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 全体
  - 初回リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関係なく本番 sqlite_path を使用する（監視テーブル初期化を含む）。
    - 例外発生時はログに残して次のポーリングに続行するフェイルセーフ実装。
    - プロセス優先度を起動時に "high" に設定する。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 専用 SQLite(DB: data/paper_trading.db 既定) に記録（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine に必要なコンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててセッションを実行。

- 設定管理
  - config.py: 環境変数読み込み・管理モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 文、クォート、バックスラッシュエスケープ、インラインコメントを考慮する堅牢な実装。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE のバリデーション、KABUSYS_ENV のバリデーション等）。
    - settings = Settings() によりモジュールインポート時に便利に利用可能。

- ポートフォリオ構築（portfolio モジュール）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で選定する関数を追加。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を計算。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックして新規候補を除外する関数を追加。sell_codes（当日売却予定）を考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告の上 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: 重み・候補・価格などから実際の発注株数（単元株丸め、リスクベース算出、aggregate cap によるスケーリング）を計算。
    - lot_size 単位で丸め、cost_buffer を用いた保守的見積り、利用可能現金を超過する場合のスケールダウンと残差の扱いを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアに固定する機能を追加（対応外や権限不足時は警告でスキップ）。

- 研究（research モジュール）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（true_range の null 伝播を注意）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0 または欠損の場合は None）・ROE を計算。
    - すべて DuckDB 接続を受け取り外部依存を持たない設計。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - 実装は外部ライブラリに依存せず標準ライブラリのみで実現。

- AI ニュース NLP
  - ai/news_nlp.py
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析の実装を追加。
    - 処理フロー: ニュースウィンドウ算出 → raw_news + news_symbols 集約 → 最大 20 銘柄ずつのバッチ送信 → リトライ（429/ネットワーク/5xx）→ レスポンス検証 → スコア ±1.0 にクリップ → ai_scores に部分置換で書き込み（DELETE/INSERT により対象コードのみ更新して部分失敗に耐える）。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - トークン肥大化対策（1銘柄あたり最大記事数・最大文字数）、JSON モード期待、フェイルセーフ設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可。
    - SQL の例外（テーブル未存在など）は捕捉してデフォルト値でレポートを生成。

Changed
- （初回リリースのため過去変更はなし）

Fixed
- （初回リリースのため過去修正はなし）

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キー未設定時は明示的に例外を発生させることで無意識の無効呼び出しを防止。

Notes / Implementation details
- DB: SQLite と DuckDB を併用。監視・発注ログ等は SQLite、分析・ファクター計算は DuckDB を想定。
- Paper Trading: 本番データと完全に分離するよう紙上トレード専用の SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
- 環境変数の自動ロード処理はプロジェクトルートを探索して行い、OS 環境変数を保護する設計（.env.local は上書き可）。
- ログレベル・閾値・各種設定は Settings クラス経由でバリデーション付き取得可能。
- 外部依存: psutil（プロセス操作）, duckdb, openai（OpenAI client）を使用。

今後の予定（例）
- 単体テスト・統合テストの追加（特に position sizing やニュース API のリトライ周り）。
- 銘柄別 lot_size 対応（stocks マスタに基づく拡張）。
- price フォールバック（前日終値等）を用いたエクスポージャー計算改善。
- AI スコア取得のより厳密なエラーハンドリング／部分再試行メカニズムの強化。

---- 

（以上）
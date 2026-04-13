CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

(なし)

0.1.0 - 2026-04-13
------------------

Added
- プロジェクト初期リリースを追加。
- 基本パッケージ情報:
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として定義。
  - __all__ エクスポートに主要サブパッケージを追加。

- 実行用スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックし、警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を high に設定（utils.process_priority を利用）。
    - SQLite / DuckDB 接続の初期化とクリーンなクローズ処理を実装。
    - KeyboardInterrupt によるループ終了処理をハンドリング。

  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は MockBrokerClient を利用する想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を high に設定。
    - DuckDB の接続を ExecutionEngine に渡す。

- 設定管理:
  - config.Settings クラスを追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメントルール等に対応。
    - 必須環境変数取得用のヘルパー _require と、各種設定プロパティ (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE など) を提供。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装（有効値チェックで不正なら ValueError）。
    - 監視・実行に必要な pid_file_path / kill_flag_path / 各種閾値設定（CPU/MEM/DISK）をプロパティで提供。

- ポートフォリオ構築関連（純粋関数群）:
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank の昇順でタイブレークし上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア比率に基づく重み。全銘柄スコアが 0 の場合は等金額にフォールバック（警告出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有ベースでセクター集中が max_sector_pct を超える場合、新規候補から除外（"unknown" セクターは適用除外）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算。lot_size（単元）丸め、max_position_pct による per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差処理（lot 単位での追加配分）などを実装。
    - risk_based: risk_pct / stop_loss_pct に基づく株数算出。
    - equal/score: weight に基づく配分と aggregate cap の実装。

- 研究・ファクター計算:
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。必要行数が足りない場合は None。
    - calc_volatility: ATR(20), 相対 ATR, 20日平均売買代金, 出来高比率を算出。true_range 計算における NULL 伝播制御を実装。
    - calc_value: raw_financials から最新の財務データと当日の価格を結合して PER・ROE を算出。
    - 各関数は DuckDB 接続と prices_daily / raw_financials テーブルを参照。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）の将来リターンを一括で取得（LEAD を使用）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量集計。外れ値や None を適切に除外。
  - research.__init__ で主要関数と zscore_normalize をエクスポート。

- AI / ニュース NLP:
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄別 ai_scores テーブルへ書き込む処理を実装。
    - ニュース収集ウィンドウ（JST 基準）を明確化し、UTC に変換して DB クエリに使用。calc_news_window 関数を提供。
    - 1銘柄あたりの最大記事数 / 最大文字数でトリム（トークン肥大化対策）。
    - 最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx に対する指数バックオフでのリトライ（上限あり）。
    - レスポンスの厳密な JSON バリデーション、スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗時の既存スコア保護を考慮して、対象コードに対して DELETE → INSERT の置換方式。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定なら ValueError。

- ユーティリティ:
  - utils.process_priority
    - set_process_priority(level): Windows (psutil の優先度クラス) と POSIX (nice 値) を吸収して実装。未対応 OS は警告してスキップ。権限不足などを例外化せず警告で処理。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定。引数検証と権限エラーの安全処理を実装。

- ツール:
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH（または --db）で DB 指定可。
    - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数を集計。
    - 判定基準（閾値）を定義し PASS/FAIL を出力（稼働率 99% など、スクリプト内定義）。
    - P95 計算、日付フィルタリング、DB 存在チェック、OperationalError に対するフォールバックを実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キー等の機密情報は環境変数経由での取得を前提。設定読み込みは .env 自動ロードを行うが、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。

Notes / Implementation details
- DuckDB と SQLite を併用する設計:
  - DuckDB は主に時系列・ファクター計算用（prices_daily / raw_financials 等）、SQLite は監視・トレードログ等の軽量トランザクション用として利用する想定。
- Paper trading と Live を分離:
  - paper_trading 環境では paper 用 SQLite を使用し、本番データと完全分離する仕様。
- フェイルセーフ & ロバストネス:
  - 外部 API 呼び出し失敗や DB テーブル未存在時に対する例外処理を多くの箇所で実装（ログ出力・フォールバック）。
- 設計思想:
  - 多くのモジュールは副作用を持たない純粋関数化を志向（テスト容易性向上）。
  - datetime.today()/date.today() を直接参照しない箇所がある（AI モジュールなど、ルックアヘッドバイアス対策）。

開発者向け注意
- .env の自動読み込みはプロジェクトルート判定に .git または pyproject.toml を使用するため、パッケージ配布後の実行環境では自動読み込みがスキップされる可能性があります。必要なら環境変数を明示的に設定してください。
- process_priority / cpu_affinity の設定は権限に依存します。CI や一部の OS ではアクセス拒否となるため、警告でスキップします。

-----------------------------------------------------------------------------
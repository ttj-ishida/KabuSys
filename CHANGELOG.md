CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

v0.1.0 - 2026-04-12
-------------------

Added
- プロジェクト初回公開相当のリリース。
- 実行/監視ランナー:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が "paper_trading" の場合、paper_trading 用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() の起動。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内で定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告ログを出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する挙動を明示。
    - プロセス優先度を起動直後に "high" に設定する仕組みを導入（set_process_priority を利用）。
- 設定/環境管理:
  - kabusys.config.Settings を導入。
    - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順: OS 環境 > .env.local（上書き可）> .env（未設定のみ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 各種環境変数アクセサ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値, LOG_LEVEL, KABUSYS_ENV 等）を提供。デフォルト値・検証（有効値チェック）を実装。
    - PAPER_FILL_MODE の有効値検証 ("instant","partial","never","reject") と例外処理。
- ポートフォリオ構築モジュール:
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。全スコアが 0 の場合は等分配にフォールバックし警告。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（デフォルト 1.0、未知レジームは警告して 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数算出。
    - 単元株（lot_size）考慮、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap を超える場合のスケールダウンと端数再配分ロジックを実装。
- リサーチ / ファクター計算:
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily から算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。欠損データハンドリング（ウィンドウ不足で None）。
    - calc_value: raw_financials と prices_daily を結合して PER/ROE を算出。target_date 以前の最新財務データを取得。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数が 3 未満なら None）。
    - factor_summary / rank: 基本統計量算出、ランク付けユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats 提供）を re-export。
- ニュース NLP / OpenAI 統合:
  - kabusys.ai.news_nlp:
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、最大文字数・記事数制限（1 銘柄あたり最大記事数/文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアクリッピング（±1.0）を実装。
    - score_news の実行には OPENAI_API_KEY（引数 api_key または環境変数）が必須。未設定時は ValueError。
    - ニュース集計ウィンドウは JST ベースで前日 15:00 〜 当日 08:30（UTC に変換して DB 比較）を採用。calc_news_window ユーティリティを提供。
    - 書き込みは対象コードのみを DELETE→INSERT することで部分失敗時の既存データ保護を図る。
- ユーティリティ:
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows/Linux/Mac の差分を吸収して現在プロセスの優先度を設定。対応 OS 以外では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定（None なら no-op）。アクセス拒否や未対応 API では警告を出してスキップ。
    - 例外発生時に警告ログを出すフェールセーフ実装。
- ツール:
  - kabusys.tools.paper_verification_report:
    - Paper Trading 用の検証レポート出力スクリプトを追加。
    - 検証基準（稼働率、注文成功率、送信率、P95 レイテンシ）と閾値を定義（稼働率 >=99.0%, fill >=90.0%, send >=95.0%, P95 <=200 ms）。
    - DB が存在しない場合のエラーメッセージ、期間フィルタ（--from/--to）、--db オプション対応を実装。
    - 各メトリクス取得時にテーブル欠損（OperationalError）をハンドリングして N/A 相当の値でレポート出力。
- パッケージメタ:
  - kabusys.__init__.__version__ = "0.1.0" を設定。
  - パッケージの __all__ に主要サブパッケージを追加。

Changed
- 初回リリースのため特段の変更履歴は無し（v0.1.0 として初期導入）。

Fixed
- 初回リリースのため "実装段階で想定した不具合回避" を複数実装:
  - .env パーサは引用符内のバックスラッシュエスケープ・インラインコメント処理に対応。
  - .env ロード時に OS 環境変数を保護する protected 機能を導入（.env.local の上書きを制御）。
  - process_priority の実行で権限不足や未サポート API に対して警告を出して処理を継続。

Security
- OpenAI API キー等のシークレットは Settings 経由で環境変数から取得。.env の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。環境ファイルを扱う際は権限管理に注意。

Notes / Migration
- 環境変数の型・有効値チェックに失敗するとアプリは ValueError を送出する箇所があります（例: KABUSYS_ENV の無効値、PAPER_FILL_MODE の無効値、LOG_LEVEL の無効値）。デプロイ前に .env（または OS 環境）を確認してください。
- run_monitoring は監視用 DB（Settings.sqlite_path）を本番 DB として使用します。開発や paper_trading で監視 DB を分離したい場合は SQLITE_PATH を明示的に変更してください。
- run_execution は paper_trading 環境時に専用 DB を使用します（PAPER_TRADING_SQLITE_PATH を上書き可）。
- news_nlp.score_news 実行時は OPENAI_API_KEY が必須。API 利用に伴うコスト・レート制限に注意してください。
- position_sizing の lot_size は現在グローバル固定（デフォルト 100）。将来的な拡張のために設計上の注記が残されています。

今後の TODO（コード内注記の抜粋）
- position_sizing: 銘柄別単元対応（lot_map）への拡張。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値等）の実装。
- ai.news_nlp: API レスポンスの部分失敗対策のさらなる堅牢化、ログの強化。
- DuckDB の executemany 制約（空パラメータの扱い）への注意点に関するドキュメント整備。

ライセンス
- 本プロジェクトのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください。
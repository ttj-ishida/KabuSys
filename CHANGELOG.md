CHANGELOG
=========

すべての変更は Keep a Changelog の仕様（https://keepachangelog.com/ja/1.0.0/）に準拠して記載しています。  
バージョニングはセマンティックバージョニングに従います。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-12
-------------------

Initial release — 初回公開リリース。

Added
- プロジェクト全体の初期実装を追加。
  - パッケージエントリポイントとバージョン:
    - kabusys.__version__ = "0.1.0"
- 実行系 / 運用スクリプト:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 環境変数 KABUSYS_ENV により paper_trading モードを切り替え、paper_trading 時は専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() 実行。
    - プロセス優先度を high に設定するユーティリティ呼び出しを実行開始直後に行う。
    - DuckDB（分析用 DB）接続を確立して ExecutionEngine に渡す。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を high にセット、SQLite / DuckDB の接続管理、例外保護された polling loop を提供。
- 設定・環境変数管理:
  - kabusys.config.Settings
    - .env ファイルの自動読み込み機能（プロジェクトルートの .git または pyproject.toml を探索基準にする）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env ファイルの行パーサ実装（コメント・export 形式・クォート・エスケープに対応）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/KILL フラグパス / PAPER_FILL_MODE バリデーション等）。
- モジュール: portfolio（ポートフォリオ構築）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選出。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコア0 の場合はフォールバックで等金額配分）。
  - risk_adjustment
    - apply_sector_cap: セクター集中を抑えるフィルタ（既存保有からセクター比率を算出し上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告のうえフォールバック1.0）。
  - position_sizing
    - calc_position_sizes: 等配分・スコア配分・リスクベース（risk_based）に基づく発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer の考慮。
    - スケーリング時の端数調整アルゴリズム（remainder を使った lot 単位での追加配分）を実装。
- research（リサーチ / ファクター計算）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 偏差を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: EPS / ROE に基づく PER・ROE を計算（raw_financials から最新レコードを取得）。
    - DuckDB を用いた SQL ベースの高性能実装。
  - feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）計算（horizons の検証あり）。
    - calc_ic / rank / factor_summary: IC（スピアマン相関）計算、ランク付け、統計サマリを実装（外部ライブラリ非依存）。
  - research.__init__ で zscore_normalize を data.stats から再エクスポート。
- ai（AI / ニュース NLP）
  - news_nlp
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し ai_scores テーブルへ書き込む処理を実装。
    - 日時ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と記事集約、1銘柄あたりの文字数・記事数トリム、最大バッチ 20 銘柄でのバッチ送信、429/ネットワーク断/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分置換によるテーブル更新などを設計通りに実装。
    - OpenAI API キー未設定時は ValueError を送出して明示的に失敗させるチェックを実装。
- tools
  - paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する実用的なサマリ出力を提供。
    - 日付フィルタ、DB 存在チェック、SQLite の OperationalError に対する堅牢なフォールバックを実装。
- utils
  - process_priority
    - set_process_priority(level): Windows / POSIX の差異を吸収してカレントプロセスの優先度を設定（high/normal/low）。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め（None の場合はスキップ）。
    - アクセス拒否や未実装例外を安全にログ警告してスキップする実装により運用時の安全性を確保。
- DB 初期化ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を起動シーケンス内で呼び出し、monitoring 用テーブルの存在を保証（冪等）。

Changed
- 設定の自動ロード挙動:
  - .env/.env.local の読み込みで OS 環境変数を保護（protected）する動作を導入。既存の OS 環境変数は上書きされない。
- .env パーサの改善:
  - export キーワード対応、クォートされた値のバックスラッシュエスケープ対応、インラインコメントの取り扱い、クォートなし値のコメント判定ロジックを実装して柔軟性を向上。

Fixed
- 環境変数バリデーションとデフォルトフォールバック:
  - MONITOR_POLL_INTERVAL の負値や非整数値に対する警告とデフォルト値フォールバックを追加（time.sleep の ValueError 回避）。
  - PAPER_FILL_MODE の不正値チェックを追加し、不正値時に明確な ValueError を発生させるようにした。
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックしてゼロ除算を回避。
- 堅牢性向上:
  - run_* スクリプトで DB 接続を finally で確実にクローズするように統一。
  - process_priority / set_cpu_affinity で権限不足や未実装 API に対して警告ログを出し処理を続行するようにした。

Security
- .env 自動ロード時に OS 環境変数を保護する実装により、外部ファイルによる運用環境変数上書きリスクを低減。

Known Issues / Notes
- position_sizing.calc_position_sizes / apply_sector_cap の一部に TODO コメントあり:
  - price が欠損（0.0）の場合にエクスポージャーやサイズが過少見積もられる可能性があるため、前日終値や取得原価をフォールバックとして使う拡張が検討課題として残されています。
- ai.news_nlp.score_news:
  - OpenAI API 利用部分はネットワークやレート制限の影響を受けるため、運用時は API キー・利用制限・課金に注意してください。失敗時はスキップして継続する設計だが、部分失敗は結果の欠損を招く可能性があります。
- DuckDB executemany に関する注意:
  - ai モジュールのコメントにある通り、executemany 前に params が空でないことを確認するなど DuckDB 特有の制約を踏まえた実装注意点があります。

Acknowledgements
- 本リポジトリはシンプルな自動売買システム（日本株想定）を想定したモジュール群を含みます。Execution / Monitoring / Portfolio Construction / Research / AI scoring / Tools といった主要機能を初期実装しました。

License
- 本リリースに含まれるファイル群のライセンス情報はリポジトリの LICENSE を参照してください。
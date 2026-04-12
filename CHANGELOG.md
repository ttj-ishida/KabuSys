CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

追加予定／進行中の作業（現時点では未リリースの変更点を記載）:
- なし（初回リリースは 0.1.0 を参照してください）。

0.1.0 - 2026-04-12
------------------

初回公開リリース。以下の主要な機能群とユーティリティを含みます。

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 設定・環境変数管理
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 複雑な .env パースを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理）。
  - 環境変数自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで各種設定プロパティを公開（DB パス、PID ファイル、監視閾値、環境種別判定、PAPER_FILL_MODE バリデーションなど）。
- 実行系（Execution）
  - run_execution.py：ExecutionEngine 起動エントリポイント
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager（デフォルト RiskConfig を内蔵）, Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を設定（high）。
    - DuckDB 接続を受けて分析用途にも対応。
- 監視系（Monitoring）
  - run_monitoring.py：SystemMonitor ポーリングループ起動エントリポイント
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは共有 DB に蓄積）。
    - 起動時にプロセス優先度を設定（high）。
- データベース初期化ユーティリティ
  - monitoring テーブル群の存在を保証する init_monitoring_db 呼び出しを各起動箇所で実行（冪等）。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）を吸収する優先度設定。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピンニングするユーティリティ。
    - 権限不足・未対応 API に対してはワーニングを出して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank タイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: スコア加重で全スコアが 0 の場合は等金額配分にフォールバック（WARNING 出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別エクスポージャー計算に基づく候補のフィルタリング（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知は 1.0 にフォールバックして WARNING）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。
    - lot_size による単元丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン（コストバッファ考慮）。
    - スケールダウン時の残差処理（lot 単位で残差が大きい順に追加配分）。
- 研究・ファクター計算（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離などを計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（DuckDB SQL ベース）。
  - research/feature_exploration.py
    - calc_forward_returns: リードを使った将来リターン計算（任意ホライズン）。
    - calc_ic: スピアマンランク相関（IC）算出、サンプル数不足時は None。
    - factor_summary / rank: 基本統計量・ランク処理ユーティリティ。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大対策（記事数・文字数上限）、結果バリデーション、スコアクリップ（±1.0）。
    - OpenAI API の一時エラー（429 / ネットワーク / 5xx）に対して指数バックオフでリトライ。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - ニュース取得ウィンドウ計算ユーティリティ calc_news_window を提供（JST→UTC のウィンドウ変換）。
    - 部分成功時に既存スコアを保護するため、対象コードに限定して DELETE→INSERT を実行する実装方針。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を判定するしきい値を内蔵（稼働率 >= 99% 等）。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト DB を上書き可能。
    - P95 を独自実装、各種 SQL 発行でテーブル存在チェックに失敗した場合は N/A 扱いで安全に報告。

Changed
- （初回リリースのため該当なし）

Fixed
- 設定/起動の堅牢化
  - MONITOR_POLL_INTERVAL に不正な値を与えた場合、例外ではなく警告を出してデフォルト（60 秒）にフォールバックする実装を導入。
  - DB 接続後に監視用テーブルの初期化（init_monitoring_db）を必ず実行して監視周りの実行時エラーを低減。
  - process priority / cpu affinity 設定で権限不足・未実装 API が発生した場合は例外を吐かずワーニングに留めることで起動失敗を防止。

Security
- OpenAI API キーは環境変数（OPENAI_API_KEY）または明示引数で供給。未設定時は明・確にエラーを返す（漏洩リスク低減のため設定を明示する必要あり）。

Notes / Migration
- 環境変数の自動ロードはデフォルトで有効。CI やテスト環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading モード（KABUSYS_ENV=paper_trading）では SQLite DB が production 用とは分離されます（デフォルト data/paper_trading.db）。本番 DB を誤って上書きしないよう注意してください。
- MONITOR_POLL_INTERVAL の単位は秒。0 や負数は無効でデフォルト（60 秒）にフォールバックします。
- PAPER_FILL_MODE の値が無効な場合は起動時に ValueError を送出します（instant / partial / never / reject のいずれかを使用してください）。
- calc_score_weights は全銘柄スコアが 0 の場合、自動的に等金額配分にフォールバックしてログに警告を出力します。

Acknowledgements
- 初回リリースにあたり、DuckDB を分析基盤として利用する設計を採用。OpenAI を用いた NLP スコアリングは外部 API に依存するため、API のレート制限やコストに注意してください。

今後の予定
- 詳細なユニットテストの追加（特に位置決めロジック・スケールダウンの端数処理）。
- 銘柄別 lot_size をサポートするための拡張（stocks マスタの導入）。
- ニュース NLP のロバストネス向上（部分失敗時のロールバック戦略の改善、より厳密なレスポンス検証）。

---
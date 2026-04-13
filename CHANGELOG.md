Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- 監視/実行プロセスの安定化・運用利便性向上
  - MONITOR_POLL_INTERVAL 環境変数のパース検証を追加（0 以下や不正値はデフォルト 60 秒にフォールバックし、警告ログを出力）。
  - 監視ループで check_once() の例外を捕捉してログ出力し、ループ継続するようにした（単一エラーでプロセス停止しないフェイルセーフ）。
  - プロセス優先度設定を早期に行うよう起動処理を統一（set_process_priority 呼び出し）。

- ドキュメント整備・実装注釈の追加
  - 各モジュールに設計方針・注意点・参照ドキュメント箇所（PortfolioConstruction.md 等）を明記。

[0.1.0] - 2026-04-13
--------------------

Added
- 基本機能: 初期公開リリース
  - 自動売買システムのコアパッケージ kabusys を追加。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
    - RiskConfig のパラメータを定義し、initial_portfolio_value をブローカーの利用可能現金で初期化。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。

- 設定管理
  - config.py: 環境変数 / .env の自動ロード機能を追加。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定をプロパティとして提供（DB パス、PID/KILL ファイル、閾値、環境種別判定、paper_trading 用設定等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全て 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限をチェックし必要な候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）を返却、未知レジームは警告して 1.0 フォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元株丸め、per-stock 上限・aggregate cap（利用可能現金でスケールダウン）、cost_buffer（手数料/スリッページ見積り）対応。
    - lot_size を考慮した残差処理で安定的にロット単位で配分。

- 監視ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告ログを出すフェールセーフ。
    - set_cpu_affinity: 指定コア数に固定するユーティリティ（権限不足時は警告してスキップ）。

- Research（DuckDB ベースの因子・解析）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー因子の計算。
    - 各関数は不足データ時に None を返すなど堅牢に設計。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（入力検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク付け（同順位は平均ランク）、統計サマリーを実装。
  - research.__init__ で主要 API をエクスポート。

- AI ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI API（gpt-4o-mini）へバッチ投げして銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日15:00〜当日08:30 JST）を UTC に変換して取得、look-ahead を避ける実装。
    - チャンクング、トークン肥大対策（記事数・文字数上限）、レスポンス検証、スコアクリップ、429/5xx/タイムアウト等でのリトライ/バックオフ、部分書き換え（DELETE→INSERT）による部分失敗耐性を実装。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドライン起動対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定（基準値定義あり）。
    - データ欠損やテーブル未存在時に安全にデフォルト値でレポート生成（OperationalError を捕捉）。

Changed
- monitoring DB 初期化を冪等に実行（init_monitoring_db を run_execution/run_monitoring 起動時に呼び出し、テーブル存在を保証）。
- run_monitoring: 監視は KABUSYS_ENV に依存せず本番 sqlite_path を参照する旨を明記（運用上の意図を明確化）。

Fixed
- .env 読み込みの堅牢化（クォート内のエスケープ、export プレフィックス、インラインコメントの扱い等）。
- 各モジュールでの None / 空データ取り扱いを整理（factor/research 関数やレポート生成で N/A を明示）。

Removed
- 該当なし。

Security
- OPENAI API キーは外部から引き渡すか環境変数 OPENAI_API_KEY を使用する仕様。未設定時は明確に例外を投げて処理を停止（誤ったキーの無処理を防止）。

Notes / Migration
- Paper Trading を行う際は KABUSYS_ENV=paper_trading を設定することで paper_trading 用 DB が使用され、本番 DB と完全に分離されます。
- .env の自動ロードはデフォルトで有効。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は正の整数を指定してください。不正値・0 以下はデフォルト 60 秒にフォールバックします。

Contributing
------------
バグ報告・機能提案は Issue を立ててください。開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで .env の自動ロードを抑制できます。
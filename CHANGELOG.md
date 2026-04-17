CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠し、人間に読みやすい日本語で記述しています。  
（内容は提示されたコードベースから推測してまとめたもので、実際のコミット履歴がある場合はそちらを優先してください。）

Unreleased
----------
- なし（現時点では最新のリリースに含まれる変更のみを記載しています）。

[0.1.0] - 2026-04-17
--------------------
最初の公開リリース（推定）。以下はコードベースに含まれる主要な機能実装および重要な設計上の決定点を、ファイル単位にまとめた概要です。

Added
- 基本パッケージ情報
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使って本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) による安全停止、実行 PID の保存（data/execution.pid）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定。

- 設定読み込み・管理
  - config.py:
    - .env / .env.local の自動ロード実装（プロジェクトルート検出ロジック: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 詳細な .env パース実装（export 形式・クォートとエスケープ・行内コメント取り扱い等）。
    - Settings クラスで環境変数をプロパティとして提供（DB パス、PID パス、しきい値、ログレベル、env 検証等）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - env/ログレベル/各しきい値のバリデーションと利便性メソッド（is_live / is_paper / is_dev）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルのスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック（warning）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有を考慮して新規候補を除外。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）と未知レジームのフォールバック警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に対応した発注株数計算。
    - lot_size（単元）丸め、単銘柄上限、aggregate cap（投下資金超過時のスケーリング）実装。
    - cost_buffer による保守的見積もり処理と残余分の優先配分ロジック。

- 研究・リサーチ機能（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を参照して各種ファクターを計算。
    - 200日移動平均やATR、ボラティリティ、出来高指標などを DuckDB の SQL ウィンドウ関数で実装。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算（入力バリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）計算（レコード不足時の None 対応）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリ（count/mean/std/min/max/median）。
  - research/__init__.py: 上記関数群をエクスポートし z-score 正規化ユーティリティを公開。

- AI — ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI (gpt-4o-mini) でセンチメント評価して ai_scores テーブルへ書き込む設計。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC 変換） calc_news_window の実装。
    - API 呼び出しに対してバッチ処理（最大 20 銘柄）、リトライ（429 / ネットワーク / 5xx）や結果バリデーション、スコアの ±1.0 クリップ等のフェイルセーフ処理を設計。
    - (注) 提供されたファイルは途中で切れているため、完全実装の一部は未確認。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加（CLI: --from / --to / --db）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL 判定を出力。
    - P95 計算、欠損テーブルへの耐性（OperationalError を捕捉して N/A を返す）を実装。
  - tools/__init__.py: パッケージ化。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) 実装（Windows と POSIX を吸収）。psutil を利用。
    - set_cpu_affinity(cpu_count) 実装（最初の N コアに固定）。
    - 権限不足や未対応プラットフォームでの安全なフォールバック（警告ログ出力）あり。
  - utils/__init__.py: パッケージ化。

- 監視データベース初期化
  - monitoring/monitoring_db.py への参照（init_monitoring_db）を利用し、監視用テーブルの冪等的初期化を実行（run_monitoring/run_execution 両方で使用）。

Changed
- 監視動作に関する設計判断（ドキュメント化）
  - run_monitoring が常に本番 sqlite_path を参照する旨を明記（環境に依存しない監視データ収集のため）。

Fixed
- 入力検証・耐障害性の強化
  - MONITOR_POLL_INTERVAL の不正値（0・負・非整数）に対するフォールバック実装（run_monitoring._get_poll_interval）。
  - .env パーサが export 形式・引用符・エスケープ・インラインコメントを正しく扱うよう改善（config._parse_env_line）。
  - position_sizing の集計スケールダウン処理で lot 単位での再配分ロジックを実装し、端数処理の安定化。
  - research/feature_exploration.calc_forward_returns の horizons 引数検証（正の整数かつ <=252）。
  - paper_verification_report の集計クエリ呼び出しを try/except で囲み、テーブルが存在しない場合でも堅牢にレポートを生成。

Security
- 環境変数取り扱いに関する注意点
  - OPENAI_API_KEY 等の必須 API キーは Settings や各関数で明示的にチェックし、未設定時は ValueError を発生させる設計（例: ai/news_nlp.score_news）。

Notes / Implementation details（設計文書的要約）
- Pure function 方針
  - portfolio/* modules および research/* は「DB 参照なし／メモリ内計算のみ」や「DuckDB 接続を受け SQL で計算」といった設計原則に基づき分離されているため、ユニットテストが容易。
- DuckDB の活用
  - 大量時系列データ（prices_daily / raw_financials / raw_news 等）の集計は DuckDB のウィンドウ関数で効率化している。
- フェイルセーフ
  - API 呼び出しや外部リソースへの依存箇所はリトライ・スキップ・ログ出力でフェイルセーフを確保している（例: OpenAI へのリクエスト、psutil の権限不足）。
- TODO / 将来改良点（コード内コメントより）
  - position_sizing: 銘柄別 lot_size 対応（将来的には stocks マスタを参照）。
  - risk_adjustment.apply_sector_cap: price の欠損時のフォールバック（前日終値や取得原価の利用）を検討。

既知の制限 / 注意事項
- ai/news_nlp.py が提示コードで途中までしか示されていないため、完全な動作仕様（記事収集ロジック、DB 書き込み部分）は未確定。
- run_monitoring は「監視 DB は常に本番 sqlite_path を使用する」旨の実装/コメントがあるため、開発環境での監視データ分離を期待する場合は設定やコードの変更が必要。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やパッケージ化後にルートが検出できない場合は自動ロードがスキップされる点に注意。

その他
- 上記は提供されたソースコードの内容から推測してまとめた CHANGELOG です。実際のコミットメッセージやリリース日付を利用した正確な履歴が必要であれば、Git 履歴に基づいて改めて生成することを推奨します。
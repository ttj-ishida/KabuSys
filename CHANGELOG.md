Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴（日本語）を作成しました。初回リリース相当の内容を 0.1.0 としてまとめています。

CHANGELOG.md
=============

すべての変更はこのファイルに記録します。フォーマットは Keep a Changelog に従います。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点での未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース — KabuSys 基本機能群を実装
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
      - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.Settings を実装。
      - .env / .env.local の自動ロード（プロジェクトルートを .git または pyproject.toml から探索）。
      - 環境変数のパース（コメント・クォート・export 形式などに対応）。
      - 各種設定プロパティ（DB パス、PID/kill flag パス、閾値、環境識別、paper_trading 関連設定など）を提供。
      - 入力値のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
  - モニタリング DB 初期化ユーティリティを実行する呼び出しを各スクリプトに追加（init_monitoring_db）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
      - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定。
      - デフォルト DB は data/paper_trading.db、コマンドライン引数で期間・DB を指定可能。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順で候補選定。score 同値の場合は signal_rank の小さい方を優先。
      - calc_equal_weights / calc_score_weights: 配分重み計算。スコア総和が 0 の場合は等金額配分にフォールバックして警告を出力。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限。既存保有のセクターエクスポージャが閾値を超える場合、新規候補をフィルタ。
        - "unknown" セクターは上限適用対象外（除外しない）。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告後 1.0 にフォールバック。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method("risk_based" | "equal" | "score") に基づいて発注株数を計算。
        - 単元（lot_size）丸め処理、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）実装。
        - cost_buffer を使って保守的に約定コストを見積もる。
        - スケールダウン時に残差（fractional remainder）を用いて lot 単位で追加配分。
  - リサーチ・解析機能（DuckDB ベース、外部 API 非依存）
    - research.factor_research
      - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
      - 欠損・データ不足に配慮した設計（必要行数未満で None を返す等）。
    - research.feature_exploration
      - calc_forward_returns: 将来リターン計算（複数ホライズン対応・最大 252 日制約）。
      - calc_ic / rank / factor_summary: IC（スピアマンのρ）計算、ランク付けユーティリティ、統計サマリー。
    - research.__init__ によるエクスポート（zscore_normalize を含む）。
  - AI ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む処理。
      - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で記事を集約。
      - 1 銘柄あたり記事数・文字数によるトリム、最大バッチサイズ 20、最大リトライ回数、指数バックオフなどを実装。
      - OpenAI API の結果を厳格に検証し、スコアを ±1.0 にクリップしてテーブルへ部分更新（DELETE+INSERT の形）するフェイルセーフ設計。
  - ユーティリティ
    - utils.process_priority: プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
      - set_process_priority(level): Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値 (-10/0/10) を利用。
      - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留めする機能。
      - アクセス権限不足や未サポート OS に対しては警告ログを出して安全にスキップ。

Changed
- 設計方針の明確化
  - research / ai モジュールは本番 API（ブローカー等）へアクセスしないよう設計（データ解析・リサーチは DuckDB に限定）。
  - 外部依存を最小化（pandas 等に依存せず標準ライブラリ + duckdb を利用）。

Fixed
- .env 読み込みの堅牢化
  - export プレフィックス、クォート文字列中のエスケープ、行内コメントの判定などを考慮したパーサを実装し、環境変数の自動ロードをより安全に。
- 各所のフォールバックと堅牢性強化
  - MONITOR_POLL_INTERVAL の不正値検出時にデフォルトにフォールバックして警告を出力。
  - DB テーブルが存在しない場合でも tools/paper_verification_report が安全に動作するよう例外をキャッチして N/A を返すようにした。
  - OpenAI API キー未設定時に明確な例外（ValueError）を投げるようにした。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で明示的に指定する必要がある旨を明記。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時の安全対策）。

Notes / Implementation details
- SQLite / DuckDB のパスは Settings で管理。Paper Trading はデフォルトで data/paper_trading.db に分離。
- run_monitoring は監視専用の sqlite（settings.sqlite_path）を使用して動作する仕様（KABUSYS_ENV に依存しない）。
- calc_position_sizes は lot_size（現在は 100）単位で丸める設計。将来的に銘柄毎の lot_size をサポートする余地を残している。
- research の集計クエリは DuckDB 上で完結するよう設計されており、営業日ベースの窓幅計算（近似で calendar 日数のバッファを取る）を行っている。

Acknowledgments
- 初期実装。以後のリリースでテスト、ドキュメント、型注釈強化、エラーハンドリングの追加、CI/CD、より詳細なセキュリティレビューを行う予定です。
CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-16
------------------

Added
- パッケージ初回公開（KabuSys）。
  - __version__ を 0.1.0 に設定。
- 実行系および監視の起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による停止制御、PID ファイル管理（data/execution.pid）を実装。
    - init_monitoring_db を呼び出し監視テーブルの存在を保証。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ data/stop_requested.flag を検知してループ終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の振る舞いを明示。
- 設定管理モジュールを追加・強化（kabusys.config）。
  - .env 自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順と上書きポリシーを実装（OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD 対応）。
  - 複雑な .env 行（export、引用文字列、インラインコメント）を扱うパーサ実装。
  - Settings クラスを追加し、J-Quants / Kabu API / DB パス / 監視閾値 / 環境種別等をプロパティで取得可能に。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV/LOG_LEVEL の検証を実装。
- Paper Trading 検証レポート用ユーティリティを追加（kabusys.tools.paper_verification_report）。
  - CLI から期間指定可能（--from / --to / --db）。
  - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計してレポート出力。
  - 合格基準（閾値）を定義（稼働率 99.0% 等）し、PASS/FAIL 判定を行う。
- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中抑制（apply_sector_cap）、市場レジームに基づく資金乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）を実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮）。
- リサーチ／ファクター計算モジュールを追加（kabusys.research）。
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、流動性指標）、バリュー（PER・ROE）を DuckDB 経由で計算。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman）計算、ファクター統計サマリー等の解析ユーティリティ。
  - DuckDB を前提とした SQL ベース実装で、外部 API には依存しない設計。
- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp：初期実装）。
  - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出する処理の骨組みを実装。
  - バッチ送信（最大 20 銘柄）、文字数・記事数のトリム、スコアクリップ（±1.0）、エラー時のリトライ（指数バックオフ）等の仕様を定義。
  - target_date ベースのニュースウィンドウ計算（calc_news_window）や API キー解決ロジックを実装。
- プロセス制御ユーティリティを追加（kabusys.utils.process_priority）。
  - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を変更（"high"/"normal"/"low"）。
  - set_cpu_affinity(cpu_count): 指定数の CPU にプロセスをピン留めするユーティリティ。
  - psutil の権限例外等を考慮して安全にフォールバック。
- パッケージのエクスポート整理。
  - kabusys.portfolio / kabusys.research の __all__ を定義し、主要関数をパッケージレベルで公開。

Changed
- .env ローダーの挙動を明確化。
  - .env.local が .env を上書きする仕様、既存の OS 環境変数の保護（protected set）を導入。
- run_monitoring / run_execution 起動時にプロセス優先度を最初に設定（set_process_priority("high")）。
- run_monitoring のポーリング間隔取得を関数化し、環境変数の不正値時に警告してデフォルトへフォールバック。
- calc_position_sizes の aggregate cap ロジックを実装／改善（スケールダウン、端数処理、lot_size 単位での再配分）。
- calc_regime_multiplier: 未知のレジームに対して警告を出しフォールバック値 1.0 を返す仕様に変更。
- research および portfolio の関数は DB を直接変更せず純粋関数（メモリ計算）として設計。

Fixed
- .env パーサのクォート・エスケープ・コメント処理の不備を改善（引用符内のバックスラッシュエスケープ、インラインコメントの取り扱い）。
- run_execution: 停止フラグが既に立っている場合はエンジンを起動せず早期終了する挙動を追加。
- paper_verification_report: DB が存在しない場合やテーブル欠如（OperationalError）に対して安全に N/A を扱うフォールバックを実装。
- process_priority: サポート外 OS の場合は設定をスキップして警告を出力するよう改善。
- feature_exploration.rank: 同順位（ties）に対して平均ランクを付与する実装を採用し、再現性のため丸め（round）を導入。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY か明示的引数でのみ受け付け、未設定時は明確にエラーを出すように変更（news_nlp）。

Notes / Known limitations
- ai/news_nlp モジュールはファイル末尾で処理フローが途中（コメント末尾で切れている）になっており、実運用前にレスポンスのパース／DB 書込部分の実装・テストが必要です。
- position_sizing の price 欠損（0.0）時の扱いについては TODO コメントが残っており、将来のフォールバック価格導入を検討中です。
- .env 自動ロードはプロジェクトルートの自動検出に依存するため、配布後や特殊なパス構成では KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を検討してください。

References
- コードベースの説明は各モジュール内の docstring / コメントに従っています。詳細な動作やパラメータのチューニングは該当モジュールの docstring を参照してください。
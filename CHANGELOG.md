CHANGELOG
=========

この変更履歴は "Keep a Changelog" の慣例に従っています。  
注: 日付はソースから推測した作業タイミングの目安です。

Unreleased
----------
### Added
- ai/news_nlp モジュールの実装を進行中。ニュース収集ウィンドウ計算、OpenAI（gpt-4o-mini）へのバッチ送信設計、スコアのクリップ／検証ポリシー、リトライ／バックオフ方針などのコア設計を追加（score_news の処理フローを実装中、記事取得部分が途中で切れています）。
- ツール群や分析機能の追加に伴う細かい改善・ドキュメント注釈（今後の安定化・テスト対応予定）。

0.1.0 - 2026-04-16
------------------
### Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（PAPER TRADING 用に data/paper_trading.db を使用する設計）。BrokerClientFactory を介したブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler / ExecutionEngine を組み立ててデーモン的にセッションを実行。停止フラグ（data/stop_requested.flag）検出で安全に停止。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグを検知して終了。

- コンフィグ・環境変数管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出し .env → .env.local を読み込み）。読み込み時の上書き制御（override / protected）を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 環境変数パーサの改善: export 形式、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメントの扱いなどに対応するパーサ実装を追加。
  - Settings クラスに多数の設定追加／検証:
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - 監視関連設定（PID ファイルパス、kill フラグパス、しきい値: CPU/MEM/DISK）
    - 環境モード検証（KABUSYS_ENV: development/paper_trading/live）
    - LOG_LEVEL 検証

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークルール（同スコアは signal_rank 小さい方優先）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み配分。全スコアが 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有時価を算出して上限超過セクターの候補除外、unknown セクターは制限対象外）。sell_codes を除外して当日売却予定分を考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の提供（未知レジームは警告を出して 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。lot_size（単元）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮した投資額スケールダウン、スケール後の残差を lot 単位で再配分するアルゴリズムを実装。

- リサーチ／ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（cnt_200 によるデータ不足判定で None を返す）を DuckDB 上の SQL + ウィンドウ関数で計算。
    - calc_volatility: ATR（20 日）・相対 ATR・20日平均売買代金・出来高比を正確な true_range の NULL 伝播ルールで算出。
    - calc_value: raw_financials から target_date 以前の最新財務データを結合して PER / ROE を計算（EPS=0 または欠損時は None）。
  - research/feature_exploration.py:
    - calc_forward_returns: 各ホライズン先の将来リターンを一括クエリで取得（horizons 検証、レンジの安全バッファ）。
    - calc_ic / rank / factor_summary: スピアマン風のランク相関（IC）計算、同順位の平均ランク計算、統計サマリ（count/mean/std/min/max/median）を純粋 Python 実装（外部依存なし）。

- 研究補助
  - research/__init__.py で主要関数と zscore_normalize の再エクスポートを追加。

- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を run_* から呼び出して監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）を吸収する優先度設定。権限不足や未対応 OS 時は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を設定（例外時は警告でスキップ）。
  - utils/__init__.py 整備。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポートを生成する CLI ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。各種 SQL クエリは日付フィルタ・NULL 安全策を備える。P95 計算、出力フォーマット、しきい値定義を実装。

- AI / ニュース解析（初期設計）
  - ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約して OpenAI にバッチ送信し銘柄別スコアを ai_scores テーブルへ書き込む設計を追加。スコアのクリップ、JSON 出力バリデーション、最大文字数や記事数のトリム、リトライ方針（429/5xx/タイムアウト）などを規定。

### Changed
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として .env/.env.local によって上書きされない。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値（非整数や 0/負値）に対して警告を出しデフォルトにフォールバックするように変更。time.sleep への不正値流出を防止。
- run_execution: paper_trading 環境では paper_sqlite_path を使用して DB を完全分離するように変更（paper/live のデータ混在を防止）。

### Fixed
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に 0 除算や不正な重みを防ぎ、等金額配分にフォールバックするロジックを追加（警告ログあり）。
- volatility / momentum / value 計算: データ不足や NULL の伝播に対する安全な処理を追加し、不完全データでも例外を出さず None を返すように安定化。
- position_sizing: lot_size による丸め・aggregate cap のスケーリングと残差配分の実装により、投下資金が available_cash を超過するケースでの不整合を解消。
- utils/process_priority: 未対応 OS や権限エラー時に例外を投げず警告で済ませるようにしてデーモン運用でのクラッシュを防止。

### Security
- OpenAI API キーの取り扱いについて、score_news は api_key 引数と環境変数 OPENAI_API_KEY の双方をサポートし、未設定時は明示的にエラーを上げることで誤使用を防止。

### Notes / Known issues
- ai/news_nlp.score_news 実装はファイル末尾で記事取得処理の途中で切れており、完全な実行パスは未完成です。Unreleased で継続実装予定。
- position_sizing の価格欠損（price==0.0）時に exposure が過少計算される旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- .env パーサは多くのケースに対応するが、極端なエスケープや複雑なネストには未対応な部分があるため注意。

References
----------
- 実装ファイル群の主な参照: src/kabusys/{config.py, run_monitoring.py, run_execution.py, portfolio/*, research/*, ai/news_nlp.py, tools/paper_verification_report.py, utils/process_priority.py}

もし特定の変更点をより詳しく分けたバージョン履歴が必要であれば、コミットログやリリース単位（機能ごと）に基づいて分割した CHANGELOG を作成します。どの粒度で出力するか指定してください。
# Keep a Changelog
すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]
- （現時点では未リリースの変更はありません。コードベースのスナップショットを基に初期リリース履歴を作成しました。）

## [0.1.0] - 2026-04-12
初期リリース（コードベースのスナップショットに基づく推定内容）

### Added
- 基本パッケージ構成
  - パッケージエントリポイント: kabusys.__init__ にバージョン情報 `__version__ = "0.1.0"` を追加。
- 設定管理
  - kabusys.config: 環境変数と .env/.env.local 自動読み込み（プロジェクトルート検出による）。  
    - .env の行解析はコメント、export プレフィックス、クォート（シングル/ダブル）、エスケープに対応。
    - OS 環境変数を保護する protected モードでの上書き読み込みをサポート。
  - Settings クラス: J-Quants / kabuAPI / LINE / DB パス /監視・閾値などの設定プロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）やログレベル検証を実装。
    - paper_trading 用の PAPER_FILL_MODE と PAPER_TRADING_SQLITE_PATH をサポート。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - paper_trading モード時は専用 SQLite ファイル（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - 実行前にプロセス優先度を設定（utils/process_priority）。
    - ExecutionEngine の組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - check_once() 実行中の例外はログ出力後に待機を継続するフェイルセーフ。
- データベース初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選定とタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が 0 のとき等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター上限チェック（既存保有のセクターエクスポージャーを計算し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知は 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に従った発注株数計算。lot_size 単位で丸め、aggregate cap によるスケーリングと残差処理を実装。
- リサーチ機能（DuckDB ベース）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: モメンタム・ボラティリティ・バリュー系ファクターを DuckDB SQL で計算。ウィンドウ不足時は None を返す等の堅牢性を確保。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンをまとめて取得（horizons 検証・範囲制限）。
    - calc_ic: スピアマンのランク相関（IC）計算。レコード不足時は None を返す。
    - rank / factor_summary: ランク計算（同順位は平均ランク）／ファクター基本統計量計算。
  - research.__init__: zscore_normalize を含めた外部公開。
- AI ニュース NLP スコアリング
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチで送信し、銘柄ごとにセンチメントスコア（-1.0 ～ 1.0）を ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、最大記事数・文字数トリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピングなどの保護機構を導入。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。
    - 書き込みは対象コードのみを置換する方式で部分失敗時の既存データ保護を考慮。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX 系を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定。権限不足等で失敗しても警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留めするユーティリティを追加（引数検証と失敗時のフォールバック）。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（期間フィルタ、稼働率・成功率・送信率・P95 レイテンシ等の指標、PASS/FAIL 判定）。
    - DB 存在チェック、OperationalError の捕捉など堅牢性を備える。

### Changed
- 環境変数ロード順の明確化
  - 読み込み優先順位: OS 環境 > .env.local > .env（既存 OS 環境を保護）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DB の用途分離
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring DB と分離する仕様を明確化。
  - run_monitoring は環境に依存せず本番 sqlite_path を監視対象に使う設計になっている（監視対象と動作環境の分離を明示）。
- ポーリング間隔の扱い
  - MONITOR_POLL_INTERVAL の値が不正（数値でない、0以下など）の場合はデフォルト（60 秒）へフォールバックし、警告ログを出力する挙動を追加。
- ログレベル / 環境値のバリデーション追加
  - Settings で KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェックを実装し、不正値での早期失敗を誘導。
- SQL/集計ロジックの堅牢化
  - DuckDB SQL でのウィンドウ関数・NULL 制御（true_range の取り扱い、cnt による条件適用等）を明確化し、誤った過大評価を避ける実装に調整。
- position sizing のスケーリング戦略
  - aggregate cap 超過時のスケーリングにおいて、小数端数の残差を lot_size 単位で再配分するアルゴリズムを導入（再現性のため tie-break に code を使用）。

### Fixed
- .env パーサの改善
  - export プレフィックス対応、クォーテーションとバックスラッシュエスケープ処理、インラインコメント処理（クォート外のみ）に対応。
  - 空行・コメント行無視、等の細かい仕様を修正して互換性を向上。
- 計算ロバストネス
  - ファクター計算・ボラティリティ計算で必要行数が不足する場合に None を返すようにし、上流での例外発生を回避。
  - calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバック（WARNING ログ）。
  - calc_regime_multiplier で未知のレジームに対して 1.0 でフォールバック（WARNING ログ）。
  - calc_forward_returns で horizons 引数の検証（正の整数かつ <= 252）を追加。
  - feature_exploration.rank で同順位（ties）を平均ランクで処理する実装により IC 計算の安定化。
- 実行時の堅牢性向上
  - run_monitoring のポーリングループで check_once() 内の例外をキャッチしてログ出力後にループ継続（単発エラーでの監視停止を防止）。
  - run_execution / run_monitoring の終了処理で SQLite / DuckDB 接続を finally で確実にクローズするように修正。
- OpenAI 周りの安全装置
  - news_nlp: API のリトライ（429 / タイムアウト / 5xx 等）とバッチ処理を実装し、レスポンスのバリデーション・スコアのクリッピング（±1.0）を追加。API キー未設定時は ValueError を送出。
  - ai_scores への書き込みは対象コードのみを置換する方針にし、部分失敗時の既存スコア保護を強化。
- Paper 検証レポートの堅牢化
  - DB 不存在時のエラーメッセージ追加、SQLite の OperationalError を捕捉して個別指標を N/A にフォールバックする処理を追加。

### Removed
- なし（初期リリース相当のため削除に関する明示はなし）

### Security
- OpenAI API キーは環境変数または明示的引数でのみ受け取り、未設定時は明示的にエラーを発生させることで誤動作を防止。

---

注記:
- 本 CHANGELOG は与えられたコードスナップショットの内容から推測して作成したものであり、実際の開発履歴・コミット履歴とは異なる場合があります。実際の変更履歴を正確に記録するには Git 等の VCS のコミットログを参照してください。
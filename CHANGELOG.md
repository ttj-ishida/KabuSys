CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン管理が初回リリース相当の変更点をまとめています（内部バージョン: 0.1.0）。

Unreleased
---------

（今後の変更履歴のために空のセクションを残しています）

0.1.0 - 初回リリース
-------------------

リリース日: 2026-04-17（推定）

Added（追加）
- 基本パッケージ骨格を追加
  - パッケージ情報: kabusys.__init__ にバージョン 0.1.0 を設定。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - export 形式やクォート、行内コメント等に対応する堅牢な .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを導入。
  - Settings クラスを追加し、各種環境設定（DB パス、KABUSYS_ENV/LOG_LEVEL バリデーション、各種閾値、paper_trading 関連パス・オプション等）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
- 実行/監視ランナー
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。スレッドで実行し停止時に安全に停止処理を呼ぶ。
    - デフォルトの RiskConfig と EngineConfig の導入（例: max_position_pct, max_utilization, rate_limit_per_sec 等の初期値）。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知・例外保護・終了時のコネクションクローズを実装。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）を導入（monitoring 用テーブルの冪等初期化）。
- プロセス優先度／CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装（Windows / POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を実装（利用可能コア数を超える場合のハンドリング含む）。
  - 権限不足や未対応環境時は警告を出してスキップするフェイルセーフ。
- Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証指標を集計し、期間指定でレポート出力。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタ、DB 存在チェック、欠損テーブルに対する堅牢性を実装。
- ポートフォリオ構築モジュール（src/kabusys/portfolio/）
  - portfolio_builder: 候補選択（select_candidates）、等金額／スコア加重（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 銘柄ごとの発注株数算出（calc_position_sizes）。リスクベース・等分配・スコア配分に対応。単元株（lot）丸め、per-position 上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積り）の考慮を実装。
- リサーチ／ファクター計算（src/kabusys/research/）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。DuckDB 上の prices_daily / raw_financials を参照して各種ファクターを計算。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで zscore_normalize を含むエクスポートを提供（kabusys.data.stats 依存）。
- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントスコアを算出して ai_scores に書き込むワークフローを実装。
  - バッチ処理（最大 20 銘柄）、記事・文字数トリム、JSON モード出力の検証、±1.0 にクリップ、429/5xx/ネットワークエラー等に対する指数バックオフリトライなどを実装。
  - OPENAI_API_KEY または引数で API キーを解決し、未設定時には ValueError を送出（利用者に明示的なキー設定を要求）。
- DuckDB / SQLite 両方の接続を受ける各種処理を導入（研究・監視・実行で使用）。

Changed（変更）
- 監視の挙動
  - run_monitoring は KABUSYS_ENV に関係なく "本番" の sqlite_path を使用するよう仕様を明確化（監視データは本番 DB に集約する設計）。
- .env の読み込み順序
  - 自動読み込みの優先順位を OS 環境変数 > .env.local > .env にし、OS 環境変数は protected として上書きされない仕様に変更。
- run_execution の DB ハンドリング
  - paper_trading 環境時は paper_sqlite_path を優先して接続することで本番 DB と完全分離するように変更。

Fixed（修正）
- .env パーサ
  - export キーワードやシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなど多数のケースに対応し、不正な行を安全にスキップするよう改善。
- position_sizing のスケーリング処理
  - aggregate cap 超過時にスケールダウン後の端数処理（lot 単位）・残余キャッシュ対処を実装し、より再現性の高い配分を行うよう改善。
- research モジュール
  - ファクター・将来リターン計算においてデータ不足時に None を返すなど、欠損データへの安全な対応を追加。
- process_priority: 未対応 OS / 権限不足時に例外を上げず警告でスキップするフェイルセーフを追加。

Deprecated（非推奨）
- なし（初回リリース）

Removed（削除）
- なし（初回リリース）

Security（セキュリティ）
- OpenAI API キーの取り扱いについて
  - API キーは引数または環境変数 OPENAI_API_KEY を明示的に指定する必要があります。自動的なキーロードに依存しないため、キー管理は利用者側で注意してください。

Upgrade notes（アップグレード注意事項）
- 監視プロセスの DB
  - run_monitoring は意図的に本番 sqlite_path を使用します。以前のバージョンで環境に応じた監視 DB を使っていた場合は運用ポリシーに注意してください（監視データが本番 DB に書き込まれます）。
- .env 自動読み込み
  - デフォルトで自動読み込みが有効です。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING の分離
  - paper_trading 環境では専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。Paper 環境で本番 DB へ影響を与えたくない場合に有効です。
- 環境変数の追加・名前
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。
  - PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB パス。
  - KILL_FLAG_PATH, PID_FILE_PATH 等のパス指定プロパティが Settings に追加されています。

Notes（補足）
- 各モジュールは外部 DB（SQLite / DuckDB）上のスキーマに依存します。導入時は必要なテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs / system_status / risk_logs 等）が存在することを確認してください。
- OpenAI 連携部分は API 呼び出しの失敗に対してフェイルセーフで動作する設計ですが、API 利用料やキー管理には十分注意してください。

問い合わせ・貢献
- バグ報告や機能改善提案はリポジトリの issue にて受け付けてください。README やドキュメント（PortfolioConstruction.md / StrategyModel.md 等）を参照のうえ報告いただけると助かります。
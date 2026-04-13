# CHANGELOG

すべての重大な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

現在の日付: 2026-04-13

## [Unreleased]

予定・既知の改善点 / TODO（コード内コメントから推測）
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を導入する予定。
- position_sizing: 銘柄ごとの単元（lot_size）を stocks マスタから取れるように拡張予定（現状は全銘柄共通の lot_size）。
- ai/news_nlp: 部分失敗時のより細かいロールバック/リトライ戦略やログ強化を追加検討。
- DuckDB executemany 周りの互換性に関する追加テストとドキュメント整備。
- モニタリング／Execution のより詳細なメトリクス出力やアラート連携（LINE など）強化予定。

---

## [0.1.0] - 2026-04-13

初版リリース — 基本コンポーネントの実装と CLI/ツール類を追加。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/設定管理を実装。自動でプロジェクトルートの .env / .env.local を読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
  - .env ファイルパーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。

- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - Monitoring は環境に依らず本番 sqlite_path を使用する挙動を明示。

- データベース / 分析基盤
  - DuckDB 接続を多箇所で利用（research, ai, run_* で duckdb.connect を使用）。
  - init_monitoring_db を呼ぶことで監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア比率配分（スコアの全てが 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターの既存エクスポージャーが上限を超える場合に新規候補を除外。売却予定コードを除外して計算。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分アルゴリズムを実装。単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮した保守的なコスト見積りとスケーリング残差処理を実装。

- リサーチ・ファクター
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の SQL ウィンドウ関数を利用し、移動平均・ATR・リターン等の指標を計算。データ不足時は None を返す設計。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを任意ホライズンで計算（ホライズンの検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算。欠損・同順位（ties）に対応。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）計算。

- AI（ニュース NLP）
  - ai.news_nlp:
    - raw_news から銘柄毎に記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む score_news を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク断/5xx での指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ等を含む堅牢な実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供（ルックアヘッドバイアス防止設計）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成 CLI を追加（--from / --to / --db オプション）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 の独自実装、SQL クエリでの集計、防御的な sqlite3.OperationalError の扱いを実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（権限不足や未対応 OS では警告ログでスキップ）。
    - set_cpu_affinity: 指定コア数への CPU affinity 設定（権限不足や未対応環境でフォールバック）。

- その他
  - 設定項目（Settings）に多数のプロパティを追加（DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_* / CPU/MEMORY/DISK 閾値 等）。
  - 環境変数の検証を強化（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェック）、未設定の必須変数は明示的なエラーを発生させる。

### Changed
- 多くの計算関数でデータ不足時に None を返すようにして、上位処理での例外発生を防ぐ形に統一。
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップする設計（配布後の安全動作）。
- run_monitoring の MONITOR_POLL_INTERVAL 未整合値（0 や負値、非数）に対しては警告ログを出しデフォルト値へフォールバックするよう変更。

### Fixed
- process_priority / cpu_affinity の権限不足や未実装 API 呼び出し時に例外を上げず警告でスキップするように改善（可搬性向上）。
- position_sizing のスケーリングロジックで端数処理・残余キャッシュ配分を導入し、可変長のスケールダウン時により再現性のある配分を実現。
- research.rank の同順位（ties）処理を平均ランクにすることでスピアマン相関の安定化を図った。
- ai.news_nlp の API キー未設定時に早期に明確な ValueError を投げるようにして、誤ったコールの混乱を防止。

### Security
- 環境変数読み込み時、既存の OS 環境変数を保護する protected キーセットを導入（.env.local の override は許すが OS 環境変数は上書きしない）。

### Notes
- OpenAI API を利用する機能（ai.news_nlp）は API キー（OPENAI_API_KEY）を必要とします。キーや機密情報は .env 等で適切に管理してください。
- paper_trading モードは実行時に DB を完全分離するよう設計されていますが、運用時はバックアップや DB パスの確認を推奨します。
- DuckDB / SQLite の互換性や executemany の制約に関しては注意（コード内に回避策・チェックを実装済み）していますが、環境差分のテストを推奨します。
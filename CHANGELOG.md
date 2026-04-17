CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています（日本語）。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------

Added
- 基本アプリケーション基盤を追加
  - パッケージ初期バージョンを定義: kabusys.__version__ = "0.1.0"。
- 実行/監視用のエントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、本番 DB と分離して MockBrokerClient を利用可能にする設計。
    - 実行中は PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止を実装。
    - ブローカーファクトリ、OrderRepository/OrderManager、RiskManager、Reconciler を組み合わせてエンジンを起動。
    - RiskConfig によるデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告しデフォルトにフォールバック。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視用 DB テーブルの初期化を保証（init_monitoring_db）。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨の振る舞いを明示。
- 設定管理モジュールを追加（kabusys.config）
  - .env の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml ベース）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env の行パーサを実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応）。
  - Settings クラスにより各種環境変数をプロパティで取得（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、PAPER_FILL_MODE の検証、DB パス、閾値など）。
  - 環境名（development / paper_trading / live）やログレベルの検証を実装。
- Portfolio 関連の純粋関数群を追加（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位 N 件選定（同点時のタイブレークロジックあり）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター別時価からブロックするセクターを決定、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告の上 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定、単元株（lot_size）丸め、per-stock および aggregate キャップ、cost_buffer を用いた保守的コスト見積りとスケール調整ロジックを実装。
    - risk_based ロジックでは stop_loss_pct と risk_pct を用いた株数算出。
    - aggregate cap 超過時のスケーリングと端数（lot 単位）配分アルゴリズムを実装。
- Research / データ計算モジュールを追加（kabusys.research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: ATR(20)、相対 ATR、20 日平均売買代金、出来高比率を算出。true_range の NULL 伝播を注意して処理。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（最新の財務データを target_date 以前から取得）。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンに対する将来リターンを一括クエリで取得（horizons の入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合、None 除外、最小サンプル数チェック）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を純粋に標準ライブラリで実装。
  - research.__init__.py で主要関数群をエクスポート。
  - DuckDB を想定した SQL ベースの計算により、外部依存を最小化。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む設計を追加。
  - ニュース収集ウィンドウ（JST 基準から UTC へ変換）計算 utility（calc_news_window）。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数/文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）、部分更新（対象コードのみ DELETE→INSERT）などの運用設計を実装。
  - OpenAI API キー解決（引数または環境変数 OPENAI_API_KEY）。不在時は ValueError を送出。
  - 注意: ファイル末尾で処理が途中で切れている箇所があり（コード断片により未完）、実運用前に完了と追加テストが必要（WIP）。
- ユーティリティを追加（kabusys.utils）
  - process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度を設定。アクセス拒否等は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアへ固定するユーティリティ。無効値チェックと例外耐性を実装。
- ツール: Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）
  - SQLite（paper_trading DB）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して CLI に出力。
  - 判定基準（閾値）を定義し PASS/FAIL を判定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms 等）。
  - --from / --to / --db オプション対応、DB 存在チェック、SQLite の OperationalError に対する保護を実装。

Changed
- DB の取り扱いに関する設計
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する旨を明確化（監視データを一箇所に集約する意図）。
  - 実行（run_execution）は paper_trading 環境では paper_sqlite_path を使用し DB を分離。
- .env の読み込み順序と上書き挙動を明確化
  - OS 環境変数を保護する protected set を導入し、.env.local は .env の上書きとして適用（ただし OS 環境変数は上書きされない）。

Fixed
- 環境変数 / 設定読み込みの堅牢性向上
  - .env 解析で export 形式、引用符つき値、バックスラッシュエスケープ、インラインコメント解析等をサポートし、実運用での多様な .env 記述に対応。
- ポジションサイズ算出ロジックの堅牢化
  - lot_size 単位での丸め、_max_per_stock による per-stock 上限、aggregate cap 超過時のスケーリングと残余キャッシュを使った端数配分を実装して、発注量決定時の不整合を軽減。

Deprecated
- なし

Removed
- なし

Security
- .env 自動読み込み時に OS 環境変数を保護（protected set）し、意図しない上書きを防止。

Notes / Known issues
- kabusys.ai.news_nlp の score_news 実装がファイル末尾で途中になっており、完全実装・統合テストが必要（WIP）。API 呼び出し・DB 更新処理を統合する前に該当箇所を完成させてください。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック）は将来的な改善点として残しています。
- run_monitoring の設計では監視 DB を本番 sqlite_path に固定するため、テスト/開発用に監視を分離したい場合は別途設定かコード修正が必要です。
- OpenAI の利用は API キーとコストに注意してください。API の障害時は設計上スキップして継続するフェイルセーフが組み込まれていますが、部分失敗時の挙動（部分的にスコアが更新される等）について運用ルールを整備してください。

---

参照:
- 主要ファイル: src/kabusys/{config.py, __init__.py, run_monitoring.py, run_execution.py, tools/paper_verification_report.py, portfolio/*.py, research/*.py, ai/news_nlp.py, utils/process_priority.py}
- バージョン: 0.1.0 (package に定義)
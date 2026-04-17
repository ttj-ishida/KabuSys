CHANGELOG
=========
すべての重要な変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------
(日付: 未リリース)

Added
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応（デフォルト 60 秒）。
  - 監視処理は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する旨を明記。
  - 停止フラグ (data/stop_requested.flag) の検知で安全にループを終了する仕組みを実装。
  - プロセス優先度を起動時に設定する処理を追加（utils.process_priority.set_process_priority を利用）。

- run_execution.py
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用して paper_trading 専用 DB（data/paper_trading.db）へ記録し、本番 DB と分離する仕組みを実装。
  - 停止フラグと PID ファイル（data/execution.pid）による起動/停止制御を実装。
  - 各種依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を起動フローとして組み立て。

- config.py
  - .env / .env.local の自動読み込み機能を導入（プロジェクトルートを検出して読み込む。無効化フラグあり）。
  - .env パーサを強化（export 形式対応、クォート内エスケープ、インラインコメント処理など）。
  - 各種設定プロパティを整理・追加（duckdb_path / sqlite_path / paper_sqlite_path / pid_file_path / kill_flag_path / 各種閾値など）。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の入力検証を追加し、不正値時に明確な例外を送出。

- tools/paper_verification_report.py
  - Paper Trading 用の検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する CLI を提供。
  - 日付レンジフィルタ (--from / --to)、DB パス指定 (--db) に対応。
  - デフォルト閾値（稼働率 99% 等）と出力フォーマットを定義。

- portfolio モジュール
  - 銘柄選定・配分・リスク調整・株数決定を行う純粋関数群を実装。
  - portfolio_builder: select_candidates / calc_equal_weights / calc_score_weights（スコア全0 の際は等配分にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限の除外ロジック）、calc_regime_multiplier（市場レジームに基づく乗数）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の各割当方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮）。

- research モジュール
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（DuckDB による SQL ベースのファクター計算）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装（将来リターン計算、スピアマン IC、統計サマリー等）。
  - DuckDB 接続を前提としており、外部 API に依存しない設計。

- ai/news_nlp.py
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む機能を追加。
  - ニュース収集ウィンドウ（JST ベース）計算、記事集約、銘柄ごとの長さ制限（記事数・文字数）、バッチ送信（最大 20 銘柄/回）を実装。
  - API 呼び出しに対する 429/ネットワーク/5xx のエクスポネンシャルバックオフ再試行、結果バリデーション、スコア ±1.0 クリップ等を実装。
  - API キー引数または環境変数 OPENAI_API_KEY を使う設計。不在時は ValueError を送出。

- utils/process_priority.py
  - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。
  - Windows と POSIX（Linux / Darwin / FreeBSD）に対応し、nice 値・優先度クラスの適用、失敗時の警告ログを実装。
  - CPU affinity を設定する set_cpu_affinity 関数を追加。

Changed
- 全体
  - 各モジュールは「DB 参照なし」や「外部 API に依存しない」といった設計方針の注記を整備。
  - 多くの関数で入力検証と欠損データに対するフォールバック（None を返す、空リストを扱う等）を明示的に実装。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックして警告を出すように修正。
- feature_exploration.rank: 丸め誤差による ties 検出漏れを防ぐため round(..., 12) を用いるよう改善。
- factor_research / volatility 等の SQL 実装で NULL の伝播を意図的に制御し、カウントや平均が過大/過小評価されないように修正（true_range の NULL 処理など）。
- paper_verification_report: データ欠損時に sqlite の OperationalError を捕捉して N/A を出すように堅牢化。

Deprecated
- なし

Removed
- なし

Security
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化できる旨を明記（テスト/CI 向けの安全策）。

0.1.0 - 2026-04-17
-------------------
Added
- 初期リリース: 以下の主要機能を実装・公開。
  - 実行系
    - ExecutionEngine の起動フロー、OrderManager/OrderRepository/RiskManager/Reconciler の骨格。
    - paper_trading モードでの MockBroker 分離と専用 DB パス対応。
  - 監視系
    - SystemMonitor をポーリングで実行する run_monitoring スクリプト。
    - 監視結果保存用の monitoring.db（SQLite）とレコード初期化ユーティリティ。
  - ポートフォリオ構築
    - 銘柄選定、重み付け、株数決定、セクターキャップ、レジーム乗数などの純粋関数群。
  - リサーチ
    - DuckDB を用いたファクター計算（Momentum/Volatility/Value）と研究用ユーティリティ（forward returns / IC / summary）。
  - AI/ニュース
    - OpenAI を用いたニュースセンチメントスコアリング基盤（設計と一部処理フロー）。
  - ユーティリティ
    - .env 読み込みユーティリティ、プロセス優先度/affinity 設定、その他ユーティリティ群。
  - ツール
    - Paper Trading 検証レポート出力ツール。

Changed
- 初期リリースに伴う設計ドキュメントの注記（PortfolioConstruction.md / StrategyModel.md 等の参照をコード中に記載）。

Fixed
- 初期版の実装における基本的な入力検証・NULL 安全性を確保。

Notes
- 多くのモジュールは「外部 API に依存しない」「DuckDB / SQLite をデータソースとする」方針で設計されています。
- 実運用では環境変数の設定やファイルパス（data ディレクトリ）の配置、OpenAI API キーの管理などが必要です。
- バージョンはパッケージの __version__ に合わせて 0.1.0 を設定。

--- 
今後の予定（例）
- 単体テストの追加および CI ワークフローの整備
- BrokerClientFactory の実装拡張とエンドツーエンドの統合テスト
- stocks マスタに基づく銘柄別 lot_size サポート（position_sizing の拡張）
- ai/news_nlp の部分失敗時リトライ戦略や結果の永続化に関する細かな改善

（この CHANGELOG は、コードベースの内容から推測して作成した変更履歴です。実際のリリースノート作成時はコミット履歴やリリース対象の差分を確認してください。）
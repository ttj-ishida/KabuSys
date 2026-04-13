CHANGELOG
=========

すべての項目は "Keep a Changelog" の形式に準拠しています。  
この CHANGELOG は提供されたソースコードから推測して作成したもので、実際のコミット履歴ではありません。

[Unreleased]
------------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本アプリケーション初期リリース。
- 実行・監視用エントリポイント:
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のセッション実行を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続して監視ループを実行。
- 設定管理:
  - kabusys.config.Settings クラスを実装。.env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）、環境変数のパース処理、必須キー検査、各種設定プロパティ（DB パス、PID / kill flag パス、閾値、環境種別、ログレベルなど）を提供。
  - .env ファイルパーサはクォート文字やエスケープ、インラインコメントの扱いに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
- 監視・運用:
  - monitoring ディレクトリ想定の初期化ヘルパー（init_monitoring_db の呼び出し）に対応。監視テーブルを冪等に初期化。
  - 監視プロセスは本番 sqlite_path を環境にかかわらず使用する設計（明示的に本番 DB を参照）。
- Execution / Paper trading:
  - Paper Trading モード（KABUSYS_ENV=paper_trading）に対応。paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - PAPER_FILL_MODE（instant / partial / never / reject）のバリデーション実装。
  - Execution 側で RiskConfig・EngineConfig を導入し、初期パラメータ（max_position_pct, max_utilization, rate_limit 等）を設定。
- ポートフォリオ構築（pure function）:
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。score が全て 0 の場合は等分にフォールバックして警告を出力。
  - portfolio.risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。unknown セクターの扱いやレジームごとの既定マッピング（bull/neutral/bear）を定義。
  - portfolio.position_sizing: 単元株（lot）丸め、risk_based / equal / score の allocation_method を実装。aggregate cap スケーリング、cost_buffer を用いた保守的見積り、残差処理（lot 単位での追加配分）まで考慮。
- リサーチ / ファクター計算:
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials テーブル参照）。MA200、ATR20、複数ホライズンのモメンタムなどを SQL で集計して返す設計。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンのランク相関）計算 (calc_ic)、rank / factor_summary（count/mean/std/min/max/median）を実装。外部依存を持たない実装。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）からエクスポートする設計。
- AI ニュース NLP スコアリング:
  - ai.news_nlp: raw_news と news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルに書き込む処理を追加。
  - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数・文字数トリム（最大記事数/文字数制限）、JSON モードでの厳密なレスポンス検証、スコアの ±1.0 クリップ、429/5xx/ネットワークエラーに対する指数的バックオフリトライを実装。
  - ニュース収集ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して処理。API キーは引数または環境変数 OPENAI_API_KEY から解決。
- ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定する閾値（稼働率 99% など）を定義。コマンドラインオプション --from/--to/--db に対応し、DB 存在チェックや欠損テーブルに対するフォールバックを実装。
- データベース / SQL:
  - DuckDB と sqlite3 の両方を利用する構成を採用（DuckDB: 大量時系列データ集計、SQLite: 監視・トレードログ等の運用テーブル）。
- ユーティリティ:
  - utils.process_priority: psutil を利用したプロセス優先度設定（Windows / POSIX 差分吸収）と CPU affinity 設定ユーティリティを追加。権限不足や未サポート環境では警告を出してスキップする安全設計。
- パッケージ情報:
  - パッケージバージョンを __version__ = "0.1.0" として定義。

Changed
- run_monitoring の設計上の決定:
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様として明示（運用上の監視データを本番に集約）。
- run_execution の DB 接続:
  - paper_trading モードでは paper_trading 用の専用 SQLite を使用して本番 DB と完全分離。

Fixed
- .env パーサの堅牢化:
  - export キーワードのサポート、クォート内部のバックスラッシュエスケープ処理、クォートなしのコメント判定などを実装し一般的な .env 形式のパースの欠陥を改善。
- report / latency 計算:
  - P95 の計算（_p95 関数）やレイテンシ集計で NULL 値やデータ欠損に対する安全なハンドリングを実装。

Security
- OpenAI API キーは明示的に引数または環境変数で与えることを必須化。未設定時は ValueError を送出して誤操作を防止。

Notes / Known limitations
- portfolio.position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_size を導入する余地がある旨コメントあり。
  - open_prices が欠損（0.0）の場合、エクスポージャーが過少見積もりされる可能性があると注記している（将来のフォールバック価格導入を検討）。
- ai.news_nlp:
  - API レスポンスが空・不正な場合はフェイルセーフでスキップし、部分的にスコアを書き換える戦略（部分失敗時に既存データを保護）。
- run_monitoring / run_execution:
  - 起動時に set_process_priority("high") を呼ぶため権限によっては警告が出るが、動作継続する設計。
- 自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされる（配布後の挙動を考慮）。

今後の改善案（推奨）
- 単体テスト・CI 用フックの追加（KABUSYS_DISABLE_AUTO_ENV_LOAD を用いる等のテスト戦略が考慮済み）。
- 銘柄別 lot_size 管理や価格フォールバックロジックの導入。
- ai.news_nlp のロギング強化と監査ログ（API レスポンスの抜粋等）に関するプライバシー・セキュリティ方針の明確化。
- run_monitoring における graceful shutdown（シグナル処理）や多プロセス化検討。

--- 
（注）本 CHANGELOG は与えられたソースコードの内容から推測して作成したもので、実際のコミットメッセージや履歴に基づくものではありません。必要であれば各機能ごとにより細かいエントリ（例: 個別関数の追加・修正）を作成します。どの粒度で記載するか指示してください。
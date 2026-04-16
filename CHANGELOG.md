CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このファイルはコードベースから推測可能な変更点・機能を記載したものであり、実際のコミット履歴に基づくものではありません。

Unreleased
----------

- なし（このリポジトリの初回公開は 0.1.0）

[0.1.0] - 2026-04-16
-------------------

Added
- 初回公開（バージョン 0.1.0）。
- 実行・監視用エントリポイントを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視初期化時に本番 sqlite_path を環境に関係なく使用する挙動を実装。
- 設定管理（環境変数読み込み）を追加:
  - config.py: .env / .env.local の自動ロード（プロジェクトルート検出付き、OS 環境変数は保護）、export 形式やクォートを考慮した .env パーサ、必須 env のチェック、各種設定プロパティ（DB パス、PID/kill フラグパス、監視閾値、PAPER_FILL_MODE 検証、KABUSYS_ENV/LOG_LEVEL の検証など）を実装。
- ポートフォリオ構築モジュールを追加:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based, equal, score）に基づく発注株数計算、単元株丸め、per-stock / aggregate cap、コストバッファを考慮したスケールダウン実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 主要関数群をパッケージエクスポート。
- リサーチ / ファクター計算機能を追加:
  - research/factor_research.py: momentum, volatility, value 等のファクター計算。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算（MA200、ATR、各種ホライズンリターン等）。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）の計算、rank ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）。外部ライブラリに依存しない純 Python 実装。
  - research/__init__.py: zscore_normalize（data.stats）との統合や主要関数のエクスポート。
- ニュース NLP スコアリングを追加:
  - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）を用いたセンチメントスコアを ai_scores に書き込む処理を実装。処理はバッチ（最大 20 銘柄）、トークン肥大化対策（記事数・文字数制限）、JSON レスポンスバリデーション、スコアクリップ（±1.0）、429/ネットワーク/5xx 等に対する指数バックオフリトライ、部分失敗に対する DB 書き込みの安全策（対象コード絞り込み）などを含む。API キーの明示的指定または環境変数 OPENAI_API_KEY を使用。
- 監視・検証ツールを追加:
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL を出力。日付フィルタ/DB パス CLI オプションを提供。
- 実行時ユーティリティを追加:
  - utils/process_priority.py: プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定、また CPU affinity を最初の N コアに固定するユーティリティを提供。Windows と POSIX（Linux/Mac/FreeBSD）をサポートし、権限不足や未対応環境では警告して安全にスキップする。
- パッケージ初期化:
  - __init__.py にバージョン（0.1.0）と主要サブパッケージの __all__ を追加。

Changed
- なし（初回公開のための機能追加が主体）

Fixed
- なし（初回公開）

Security
- なし（ただし env ロード時に OS 環境変数を保護する設計を採用）

Notes / Behavior and safeguards (推測に基づく実装上の注意点)
- .env 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。プロジェクトルートが検出できない場合は自動ロードをスキップ。
- .env ローダは既存 OS 環境変数を保護するために保護集合（protected）を導入。`.env.local` は `.env` の値を上書き可能（ただし OS 環境変数は上書きされない）。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等は値検証を行い、不正な値があると例外を投げる。
- run_monitoring は監視 DB（monitoring）を環境に依存せず本番 sqlite_path に接続する（設計上の意図として監視は常に本番 DB を参照する想定）。
- run_execution は paper_trading の場合に DB を完全分離して使用（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）。
- AI スコアリングは API 呼び出し失敗時にエラーを投げず部分的にスキップして継続するフェイルセーフ設計（ただし API キー未設定時は ValueError）。
- CPU 優先度や affinity の設定は権限やプラットフォームにより失敗する可能性があり、その場合は警告ログを出して処理を続行する。

Acknowledgements / Documentation pointers
- 各モジュールの docstring に実装方針や外部参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及があり、アルゴリズムの出自が示されています。
- research / portfolio / execution / monitoring / ai の各モジュールは DuckDB / SQLite を使ったデータ駆動設計になっており、実稼働の安全策（paper_trading の DB 分離、監視ループの停止フラグ、PID 管理等）が組み込まれています。

今後の提案（実装上の改善候補）
- position_sizing の lot_size を銘柄毎に指定可能にするためのマスタ（stocks）連携。
- price 欠損時のフォールバック（前日終値や取得原価）を実装し、apply_sector_cap などで過少見積りを避ける。
- ai/news_nlp のロギング・モニタリングを強化し、失敗したコード一覧のリトライ／アラート機構を追加。
- 単体テスト・統合テスト（特に DuckDB SQL 部分）を整備して、回帰を防止。

---- End of changelog ----

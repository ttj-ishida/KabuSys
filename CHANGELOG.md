CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。
日付はリリース時点で推定しています（コードベースからの推測に基づく初期リリース記録）。

Unreleased
----------

- 特になし。

0.1.0 - 2026-04-13
------------------

Added
- 基本アプリケーション初期実装を追加。
  - パッケージのバージョンを設定（kabusys.__version__ = "0.1.0"）。
- 実行・監視のエントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db、環境変数で上書き可）を使う実装。
    - BrokerClientFactory を用いて本番／モックブローカーを切り替え。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用している旨の挙動。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理（環境変数・.env ローダー）。
  - Settings クラスを追加（kabusys.config）。
    - .env / .env.local の自動読み込み（OS 環境変数を優先、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 各種設定プロパティ（DB パス、PID/KILL ファイルパス、閾値、ログレベル、env 判定など）。
    - PAPER_FILL_MODE（paper trading の fill モード）や PAPER_TRADING_SQLITE_PATH のサポート。
    - env 値・LOG_LEVEL・PAPER_FILL_MODE のバリデーション実装。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db を run スクリプトで利用）。
- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）。
  - SQLite の paper_trading DB を解析して稼働率、注文成功率・送信率、P95 レイテンシ、リスク却下数などを集計・判定する CLI ツール。
  - --from / --to / --db オプション対応。閾値による PASS/FAIL 判定と分かりやすい出力。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）。
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコア順で上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等配分／スコア加重配分。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェックと候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・資産状況から発注株数を計算（risk_based / equal / score 対応）。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）や lot_size（単元）調整、cost_buffer 考慮。
- 研究（research）モジュールを追加（DuckDB を用いたファクター計算等）。
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン・MA200乖離率。
    - calc_volatility: ATR20、ATR比率、20日平均売買代金、出来高比。
    - calc_value: PER / ROE（raw_financials と prices_daily を組み合わせて算出）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。
    - calc_ic / rank / factor_summary: IC（スピアマン）、ランク付け、統計サマリー。
  - research パッケージはデータ処理を DuckDB に委譲し、外部 API へはアクセスしない設計。
- AI ニュース NLP スコアリング機能を追加（kabusys.ai.news_nlp）。
  - raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信、各銘柄ごとにセンチメントスコア（-1.0〜1.0）を ai_scores に書き込む処理を提供。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
  - バッチサイズや文字数上限、トークン肥大対策、最大リトライ (429/5xx/タイムアウト系) と指数バックオフの実装方針を備える。
  - API キー解決（引数または環境変数 OPENAI_API_KEY）、未設定時は ValueError を送出。
  - レスポンス検証・スコアのクリッピング（±1.0）、部分失敗時にも他銘柄の既存スコアを保護する DB 更新戦略（対象コードに絞って DELETE → INSERT）。
- ユーティリティを追加・強化。
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）差異を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留め（エラー時は警告でスキップ）。
- package のエクスポート整理（portfolio / research の __all__ 等）。

Changed
- n/a（初回リリースのため変更履歴はなし）。

Fixed
- n/a（初回リリースのため修正履歴はなし）。

Notes / Implementation details（コードから推測される重要な挙動）
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下が設定された場合、ログ警告を出してデフォルト 60 秒にフォールバックする。
- Settings の .env ローダーはプロジェクトルート（.git または pyproject.toml）を探索して自動読み込みする。テスト時等に自動読み込みを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- Paper Trading 環境は本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
- research 及び ai モジュールは本番発注 API へアクセスしない設計思想（DuckDB / ファイル DB を用いた解析、検証目的のコード分離）。
- OpenAI 連携部分はフォールトトレラント（リトライ・部分更新戦略）で、API トークン未指定時は明示的にエラーを出す実装。
- ポートフォリオ関連の関数群は副作用を持たない純粋関数であり、単体テストがしやすい設計になっている。

Security
- OpenAI API キーや各種トークンは Settings や環境変数経由で管理する仕様。サンプルやコード中に直接埋め込まれていないことが前提。

今後の検討事項（コード内コメントより）
- position_sizing: 銘柄別 lot_size を導入して単元を銘柄ごとに管理する拡張。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値など）を導入して保守的なエクスポージャー評価を行う改善。
- news_nlp: API レスポンスの堅牢な検証や部分失敗時の運用改善（ログ・再試行ポリシーのチューニング）。

---

この CHANGELOG はコード内のコメント・実装を基に自動推測して作成しています。実際のプロジェクト運用に合わせてカテゴリや日付・詳細は適宜調整してください。
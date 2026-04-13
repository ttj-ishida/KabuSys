# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このドキュメントはコードベースから推測して自動生成した初回リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

---

## [Unreleased]

（現時点のリポジトリは初回リリース相当のため Unreleased に未記載の変更はありません）

---

## [0.1.0] - 2026-04-13

### 追加 (Added)
- プロジェクト初期版を公開。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。Broker クライアントのファクトリ利用、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、EngineConfig（target_date）を用いたセッション実行を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する旨を実装。
- 環境設定管理
  - config.py: 環境変数・.env 自動読み込み機能を実装（プロジェクトルート検出: .git or pyproject.toml）。.env/.env.local の優先順位、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、.env のパース（export/クォート/インラインコメント対応）、各種設定プロパティ（DB パス、PID/KILL フラグ、しきい値、PAPER_FILL_MODE、env/log level のバリデーションなど）を提供。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: シグナル候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクター取り扱い・ログ出力を備える。
  - portfolio/position_sizing.py: position size 計算（calc_position_sizes）を実装。allocation_method ("risk_based", "equal", "score") 対応、lot_size（単元株）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap（スケーリングと remainder による再配分）を実装。
  - package エクスポート（kabusys.portfolio）にて主要関数を公開。
- 研究（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily/raw_financials を想定した SQL ベースの高速集計を行う。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。外部ライブラリに依存せず純粋 Python 実装。
  - research/__init__.py: 主要 API をエクスポート（zscore_normalize は kabusys.data.stats から参照）。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）、チャンクバッチ（最大 20 コード）、トークン肥大対策（記事数・文字数制限）、スコアのクリップ、API リトライ（指数バックオフ）等を備える。レスポンスは厳密な JSON（{"results":[...]}）を期待。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX（Linux, Darwin, FreeBSD）を考慮し、アクセス権限不足時は警告してスキップする。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を参照し、システム稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する。コマンドライン引数 --from/--to/--db をサポート。各指標の閾値はソース内定数として明示（稼働率 99%、注文成功率 90% 等）。
- パッケージ情報
  - __init__.py にバージョン文字列 __version__ = "0.1.0" を追加。

### 変更 (Changed)
- なし（初回リリースのため既存からの「変更」はありませんが、設計上の注記・既知のデフォルトをソース内に記載）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注記 / 実装上の注意点 (Notes)
- run_monitoring は KABUSYS_ENV に依らず settings.sqlite_path（本番想定の監視 DB）を使用します。対して run_execution では paper_trading 環境時に専用の paper_sqlite_path を使用して DB を分離しています。
- config.py の .env 読み込みは OS 環境変数を保護するための protected セットを扱います。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- position_sizing の aggregate cap は lot_size 単位での丸めと残余分配ロジックを持ちますが、価格欠損時の処理は現状簡易（price が 0 の場合はスキップ）で、将来的にフォールバック価格の導入をコメントで示しています。
- research モジュールは DuckDB のテーブル構造（prices_daily, raw_financials など）を前提とした実装です。外部 API 呼び出しは行いません。
- ai/news_nlp の score_news は OPENAI_API_KEY の設定を要求します。未設定時は ValueError を送出します。
- utils/process_priority は psutil に依存します。環境によっては AccessDenied などで設定がスキップされる可能性があります（警告ログを出力）。

### 既知の制約 / 将来の改善案 (Known issues / TODO)
- position_sizing: 銘柄別の lot_size をサポートしていない（将来的に銘柄マスタ経由で拡張予定）。
- risk_adjustment.apply_sector_cap: price_map に欠損値 (0.0) があるとエクスポージャーが過小見積りされる点は TODO コメントあり。
- ai/news_nlp: OpenAI のエラー種類に対する再試行戦略は実装済みだが、レート制限や大規模失敗時の耐性向上は継続的な運用観測が必要。
- tools/paper_verification_report: DuckDB ではなく SQLite の paper_trading DB を参照する設計のため、DuckDB テーブルと同期されていない可能性に注意。

### セキュリティ (Security)
- 特になし。

---

（注）本 CHANGELOG は提供されたコードの内容から機能・仕様を推測して記載しています。実際のリリースノートとして使用する場合は、プロジェクトのリリース管理者が差分やリスクを確認のうえ適宜修正してください。
# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- 変更の重大度は Breaking / Added / Changed / Fixed / Removed / Security のカテゴリで分類しています。
- 日付は本リリースを推測して付与しています（コード内容からの推測に基づくため、実際のリリース日とは異なる可能性があります）。

なお、本CHANGELOGは提供されたコードベースの内容から実装された機能・仕様を推測して作成しています。

## [Unreleased]

- ドキュメント的な追記や細かなログ/メッセージ改善等の小規模改善を予定。

---

## [0.1.0] - 2026-04-12

### Added
- 実行・監視用のエントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。環境に応じて paper_trading 用 DB を分離し、BrokerClientFactory でブローカークライアントを生成してセッションを実行する。
  - run_monitoring.py: SystemMonitor を定期ポーリングするスクリプト。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）に対応。

- Paper Trading（模擬取引）対応
  - KABUSYS_ENV=`paper_trading` の場合、paper 用専用 SQLite DB (`data/paper_trading.db` デフォルト) を利用する設計を導入。
  - MockBrokerClient を利用することで本番 DB / API と明確に分離。

- 設定管理モジュールを実装（kabusys.config）
  - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - `.env` / `.env.local` の優先度制御（`.env.local` は上書き、OS 環境変数は保護）。
  - 複雑な .env の行パースに対応（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理等）。
  - 必須環境変数チェック（未設定時は ValueError を送出）。
  - 各種設定プロパティを提供（DB パス、PID/kill フラグパス、閾値、紙取引モード、環境・ログレベル判定など）。

- 監視・モニタリング関連
  - monitoring_db 初期化ユーティリティを利用して監視テーブル存在を保証（冪等）。
  - run_monitoring が常に本番用 sqlite_path を使用する設計（監視データは本番 DB を想定）。

- Execution（注文実行）コンポーネント群（初期実装）
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine / Reconciler 等の組み立てに必要な呼び出しを実装。
  - デフォルトの RiskConfig 値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - ExecutionEngine に DuckDB 接続や pid_file パスを注入して run_session を実行。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック挙動をログ出力。
  - position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した手数料/スリッページ推定を実装。
  - risk_adjustment: セクター上限チェック（apply_sector_cap）と市場レジームに応じた乗数算出（calc_regime_multiplier）を実装。

- 研究・ファクター計算（kabusys.research）
  - factor_research: モメンタム（1/3/6か月リターン、MA200乖離率）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を提供。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman のランク相関）計算、ファクター統計サマリー、rank ユーティリティを実装。外部ライブラリに依存しない純標準ライブラリ実装。
  - 結果は日付・コード単位の辞書リストで返す設計。

- AI ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析機能を実装。
  - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数・文字数でトリム、最大 20 銘柄/チャンクでバッチ送信。
  - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に他銘柄スコアを保護するための部分置換（DELETE→INSERT）戦略を採用。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
  - ニュース収集ウィンドウ（JSTベース）の明示的計算ユーティリティを提供（calc_news_window）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシなどを計算・判定し CLI 出力する。SQLite パスの指定に対応（引数/環境変数）。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows / POSIX サポート）、CPU affinity 設定関数を実装。アクセス拒否等は警告でスキップ。

### Changed
- 環境設定読み込みの挙動
  - OS 環境変数を保護した上で .env/.env.local を自動読込（プロジェクトルートが特定できない場合はロードをスキップ）。
  - .env パース挙動を強化し、引用符・エスケープ・インラインコメントを適切に扱うようにした。

- 監視ループの健全化
  - MONITOR_POLL_INTERVAL が不正（非整数・0 以下等）な場合に警告を出してデフォルトにフォールバックする実装を追加。
  - SystemMonitor の check_once() 内で発生した例外は捕捉してログを出力し、次ポーリングへ継続するフェイルセーフ動作を採用。

- Execution 起動順序
  - プロセス優先度設定を起動直後に行う設計に統一（set_process_priority("high") を起動時に呼び出し）。

### Fixed
- .env のパースに関する取りこぼしや export プレフィックス非対応などの問題を回避する改善を実装（引用符内のバックスラッシュエスケープ・コメント判定の細部処理を追加）。
- ファクター系／統計系関数での境界条件（データ不足時に None を返す等）を明確化し、上流での例外発生を防止。

### Removed
- （本バージョンでは該当なし：機能削除は実装からは検出されず）

### Security
- 環境変数の必須チェックを強化：
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須変数は Settings 内で未設定時に ValueError を送出することで起動時に明示的に検出。
  - OpenAI API 利用時は明示的に API キーが必要で、未設定時は ValueError を発生させて処理を中断。

---

注記:
- 本 CHANGELOG は提供されたソースコードを読み取り、実装内容・設計意図・想定動作から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
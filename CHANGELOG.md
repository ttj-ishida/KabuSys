# CHANGELOG

すべての重要な変更をこのファイルに記載します。本ファイルは Keep a Changelog の慣例に準拠します。  

フォーマット:
- Unreleased: 現在の開発ブランチ（未リリース）の変更点
- 各リリースはバージョンと日付を付記

---

## [Unreleased]

### Added
- ニュースを用いた AI センチメントスコアリング機能を追加（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのスコアを ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、1銘柄あたりの最大記事数/文字数、スコアの ±1.0 クリップ等の安全策を導入。
  - API 呼び出しに対して 429/ネットワーク断/5xx を想定した指数バックオフリトライ処理を実装。
  - 入力/出力の厳格なバリデーションと、部分失敗時にも既存スコアを保護する DB 更新戦略を採用。

- DuckDB ベースのファクター計算（kabusys.research.factor_research）
  - Momentum / Volatility / Value ファクター計算を実装。200日移動平均、ATR、出来高・売買代金指標、PER/ROE 等を算出。
  - prices_daily / raw_financials テーブルを想定した効率的な SQL クエリを採用。

- 研究用ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算（複数ホライズン対応）、Spearman ランク相関 (IC) 計算、ファクター統計サマリを実装。
  - 外部ライブラリに依存せず標準ライブラリだけで計算する設計。

- ポートフォリオ構築関連（kabusys.portfolio）
  - 候補選定（score / signal_rank に基づく整列）、等配分／スコア加重配分の重み計算を実装。
  - セクター集中上限を評価・除外する apply_sector_cap を実装。既存保有の時価ベースで評価し、unknown セクターは上限適用除外。
  - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をハードコード）。
  - 株数決定ロジック calc_position_sizes を実装。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、aggregate cap のスケーリング、手数料等を想定した cost_buffer を考慮。

- 実行・監視起動スクリプトを提供
  - 実行エンジン起動スクリプト run_execution（ExecutionEngine の組み立て、paper_trading 用 DB 分離、リスク設定のデフォルト）
  - システム監視ポーリングループ起動スクリプト run_monitoring（MONITOR_POLL_INTERVAL によるポーリング間隔上書き、常に本番 sqlite_path を監視用に使用）

- 紙取引検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - Paper Trading DB を解析して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を出力する CLI ツールを追加。

- 柔軟な設定読み込み（kabusys.config）
  - .env/.env.local 自動読み込み（プロジェクトルートは .git / pyproject.toml 基準で探索）。OS 環境変数優先、.env.local は override。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env 行パーサーを拡張し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - 各種設定プロパティ（OPENAI 等は例外的必須 / デフォルト値を明示）。PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の許容値チェック、各種閾値やパスの取得関数を実装。

- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX 差分を吸収する set_process_priority 実装（high/normal/low）。
  - set_cpu_affinity によるカレントプロセスのコア固定機能。権限不足や未対応環境は警告してスキップ。

### Changed
- run_execution / run_monitoring で起動時にプロセス優先度を "high" に設定するように変更（早期に優先度を上げることで実行の安定化を図る）。
- monitoring 用 DB 初期化処理（init_monitoring_db）を両スクリプト実行時に呼び出し、監視用テーブルの存在を保証（冪等に実装）。

### Fixed
- .env ローダーの保護ロジックを改善し、OS 環境変数を保護（protected セット）した上で .env.local の override を適切に扱うように修正。
- position_sizing のスケーリングロジックで端数処理と残余配分を安定化。lot_size 単位での追加配分順序を安定化するため残差ソートにコードを二次キーとして導入。

### Notes / TODO
- position_sizing: price 欠損時のフォールバック（前日終値や取得原価）の利用は TODO としてコメント済み。
- 一部モジュール（AI スコアリングの DB 書き込み部分や OpenAI レスポンス処理）は冗長性・部分失敗時のリカバリを考慮しているが、実運用前に API のレート制限・コスト試算を行うことを推奨。

---

## [0.1.0] - 2026-04-12

最初の公開リリース。下記主要機能を含む。

### Added
- コアライブラリの初期実装
  - 自動売買システムの主要コンポーネント群（execution, monitoring, portfolio, research, ai, tools, utils）。
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等の枠組み（各種インターフェースを定義し、Broker クライアントの注入を想定）。
  - DuckDB と SQLite を組み合わせたデータアクセス層を採用（prices_daily / raw_financials / 各種ログテーブル想定）。

- 監視機能
  - system_status をポーリングして稼働状況を記録する SystemMonitor（run_monitoring 起動スクリプト）。

- 紙取引（Paper Trading）対応
  - KABUSYS_ENV=paper_trading をサポートし、paper_trading 用専用 SQLite DB を使用して本番 DB と完全分離。

- 設定管理
  - Settings クラスにより環境変数/ .env の統一的な取得とバリデーションを提供。
  - デフォルトパス（data/ 以下）や PID / kill flag の設定をプロパティ化。

- 研究・バックテスト支援
  - ファクター計算および特徴量解析ユーティリティ群（momentum/volatility/value、forward returns、IC、統計サマリ）。

- ユーティリティ
  - process_priority と CPU affinity のクロスプラットフォームユーティリティ。
  - .env パーサーは export 形式やクォート・エスケープ・コメントを扱えるように実装。

### Changed
- 初期化／起動処理はログレベル INFO を既定に設定。
- 実行環境に応じた DB パス選択ロジック（paper_trading の分離）を導入。

### Fixed
- 基本的なエラーハンドリングとリソースクローズ（DB コネクションの finally でのクローズ）を実装。

---

メモ:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や設計意図に基づく公式な変更履歴として利用する場合は、該当リポジトリのコミットログやリリースノートと照合してください。
# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理されています。  

フォーマット:
- Unreleased: 現在開発中の変更（将来リリース予定）
- 各バージョンごとに日付とカテゴリ別の要約を記載

※以下の変更点はリポジトリ内のソースコード（src/ 以下）から実装内容を推測してまとめたものです。

## [Unreleased]

### Added
- run_monitoring スクリプト
  - SystemMonitor のポーリングループ起動用エントリポイントを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用する設計。
  - プロセス優先度を起動時に "high" に設定する処理を導入。

- run_execution スクリプト
  - ExecutionEngine の起動用エントリポイントを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と完全分離。
  - BrokerClientFactory 経由で本番 / モックブローカーを切り替え可能。
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler を組み合わせてセッション実行。

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込みする仕組みを導入（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサの実装を強化（export 形式、クォート内のエスケープ、インラインコメントの扱いをサポート）。
  - 環境変数読み取り用の Settings クラスを提供。多くの設定値（DB パス、PID ファイル、閾値、PAPER_FILL_MODE など）に既定値と検証を実装。
  - KABUSYS_ENV / LOG_LEVEL 等の許容値検証を追加。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等分配・スコア加重（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出ロジックを実装。単元（lot）丸め、per-stock cap、aggregate cap（available_cash に基づくスケールダウン）を実装。

- 研究 / 分析ツール（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算関数（DuckDB を用いた SQL 実装）。MA200、ATR、平均売買代金、PER/ROE などを算出。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ランク付けユーティリティ、ファクター統計サマリー。
  - すべて外部 API に依存せず DuckDB 上の prices_daily / raw_financials 等のテーブルのみを参照する設計。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ保存するフローを実装。
  - チャンク単位（デフォルト 20 銘柄）・記事/文字数上限（記事数・文字数限定）・JSON モード出力を前提とした堅牢化。
  - 429 / ネットワーク / 5xx 等に対する指数バックオフリトライを組み込み、API キー未設定時は明示的エラーとする。
  - 出力検証・数値クリップ（±1.0）・部分失敗時の既存データ保護（影響するコードのみ置換）などのフェイルセーフ設計。

- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX(Linux, macOS, FreeBSD) を吸収したプロセス優先度設定（set_process_priority）を追加。アクセス権限や未対応 OS の場合は警告を出してスキップ。
  - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。利用可能コア数を超える指定や権限不足を安全に扱う。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成スクリプトを追加。
  - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などの指標を集計して PASS/FAIL 判定を出力。
  - P95 の計算、日付フィルタ、DB 存在チェック、SQLite のテーブル欠落時のフォールバック処理を実装。

### Changed
- 実行コンポーネントの DB 接続設計
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を参照する方針を明示化。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用し、本番データと分離。

- 設定の安全性向上
  - .env 自動読み込み時に OS 環境変数を保護するため protected set を導入し、.env.local での上書きを制御。

### Fixed
- 各コンポーネントにおいて DB 接続クローズ処理を finally ブロックで保証（run_monitoring/run_execution）。

### Known limitations / TODO
- position_sizing.calc_position_sizes
  - price が 0.0 の場合にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価をフォールバック価格として使う拡張を検討（TODO コメントあり）。
  - lot_size は現状グローバル固定（100）で、将来的に銘柄別 lot_map へ対応予定。

- ai.news_nlp
  - OpenAI の応答の完全性（モデルの JSON 整合性）に依存するため、失敗ケースを慎重に扱う実装になっている。部分失敗の際は他銘柄の既存スコアを守る設計だが、外部 API の連続失敗時の運用ポリシーは運用上の判断が必要。

---

## [0.1.0] - 2026-04-13

初回公開（推定）リリース。上記「Added」に挙げた主要機能を含む初期バージョン。  
- コア機能
  - ExecutionEngine 起動、ブローカー抽象化（本番 / モック切替）、OrderRepository/OrderManager/Reconciler/RiskManager による発注フロー。
  - SystemMonitor による定期監視ループ（監視 DB 初期化含む）。
  - ポートフォリオ構築（候補選定・重み付け・リスク調整・株数算出）。
  - 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）。
  - Paper Trading 検証レポート出力ツール。
  - 環境変数管理 (.env 読み込みの堅牢化)。
  - OpenAI を用いたニュース NLP スコアリングの骨格。

- 安全性・運用向け実装
  - プロセス優先度設定（set_process_priority）および PID / kill flag 関連設定。
  - DB 接続とリソースの確実なクローズ。
  - 各種閾値（CPU/MEM/DISK など）を Settings で管理し検証を実装。

---

注: 上記はソースコードのコメント・実装内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。必要であれば、もっと細かなコミット単位や利用者向けの移行手順（環境変数一覧、デフォルトパス、運用上の注意点等）を追記します。
# Changelog

すべての重要な変更はこのファイルに記載します。形式は「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （現在のスナップショットに対する未リリースの変更はありません）

## [0.1.0] - 2026-04-16
初回リリース。システム全体のコア機能（監視・実行・ポートフォリオ構築・リサーチ・ツール群・ユーティリティ）を実装。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - Settings クラスによる環境変数中心の設定読み込み/検証機能を実装。
    - .env / .env.local の自動読み込み（OS 環境変数を保護しつつ .env.local が上書き）
    - 必須キー読み取り `_require()`、env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）
    - DB パス、Paper Trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）など多数のプロパティを提供。

- 実行系 / エンジン関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite を使用し本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動/停止ロジックを実装。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に停止。
    - プロセス優先度を起動時に設定（utils.process_priority）。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は常に本番用 sqlite_path を使う（KABUSYS_ENV に依存しない挙動）。
    - stop フラグファイル検知・例外捕捉・リソースクローズ処理を実装。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコア降順・タイブレーク処理、スコアが全て 0 の場合のフォールバック等。
  - risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。
    - セクター別エクスポージャー計算、売却予定銘柄の除外、unknown セクターの扱い等。
    - レジームに対するデフォルトマップ（bull, neutral, bear）とフォールバック動作。
  - position_sizing.py: 発注株数決定ロジック（allocation_method: risk_based / equal / score）。
    - 単元株丸め、ポジション上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した保守的見積り。
    - スケーリング時の再配分アルゴリズム（fractional remainder を用いた lot 単位での追加配分）を実装。

- リサーチ（Research）
  - research パッケージに以下を実装:
    - factor_research.py: モメンタム / ボラティリティ / バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を用いた SQL ベースの計算。移動平均・ATR・各種リターンを営業日ウィンドウで算出。
      - データ不足時は None を返す設計。
    - feature_exploration.py: 将来リターン算出（calc_forward_returns）、IC（calc_ic）、基本統計（factor_summary）、rank ユーティリティ。
      - 外部ライブラリ不要・標準ライブラリのみでの実装。
    - research.__init__ から主要 API をエクスポート（zscore_normalize も利用可能）。

- AI / NLP
  - ai/news_nlp.py: ニュース記事の OpenAI を用いたセンチメントスコアリング基盤を追加。
    - ニュース収集ウィンドウ計算（calc_news_window）。
    - バッチサイズ、トリム（記事数／文字数上限）、スコアクリップ、リトライ（429/5xx/ネットワーク）と指数バックオフ等の設計を反映した score_news の骨格を導入。
    - 出力 JSON のバリデーション方針、部分更新（対象コードのみ置換）などを設計に明示。
    - （実装内に大きな設計方針とエラーハンドリングが組み込まれているが、ファイル末尾で記事取得処理の続きが途中切れの箇所が存在。）
  
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出して判定（PASS/FAIL）。
    - デフォルト閾値を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
    - 日付フィルタの SQL 組み立て、P95 算出、出力フォーマットを実装。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity の跨プラットフォームユーティリティ。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応した優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - アクセス拒否や未対応環境時に警告して安全にスキップする実装。
    - set_cpu_affinity によるコア固定機能（cpu_count の検証含む）。

### Changed
- 環境読み込み実装
  - .env パーサーの改良:
    - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い（クォート外での "#" の扱い）を実装。
    - 自動ロードはプロジェクトルート検出（.git または pyproject.toml）を基に行うため、CWD に依存しない。
    - OS 環境変数を保護する protected 機構を採用（.env.local の上書きルールを安全に実現）。

### Fixed
- ロバストネス向上
  - モニターループ・実行エンジンの停止検出とリソースクローズ（SQLite / DuckDB）の確実化。
  - run_monitoring の MONITOR_POLL_INTERVAL が不正（0 以下や整数でない）な場合にログを出しデフォルトへフォールバックする処理を追加。
  - Paper verification report において、DB 未存在時の明示的なエラーメッセージと sqlite3 エラー時のフォールバック処理を追加。

### Security
- OpenAI API キー管理
  - news_nlp.score_news は API キーを引数または環境変数 OPENAI_API_KEY から解決し、未設定時には ValueError を投げて明示的に扱うようにした。

### Notes / TODOs
- ai/news_nlp.py の記事取得部分（_fetch_articles の呼び出し以降）がファイル末尾で途切れているため、完全実装の確認が必要。
- position_sizing.calc_position_sizes の price 欠損時の挙動について注記（TODO）あり：前日終値や取得原価を使ったフォールバックの検討が残っている。
- 将来的な拡張として、銘柄ごとの単元株数（lot_size）を銘柄マスタに持たせる設計変更を想定したコメントあり。

---

参照: リポジトリ内の各モジュール（src/kabusys/**）を基に作成。コード内コメントに基づく設計方針・挙動・既知の制約を要約しています。必要であれば各ファイルごとの詳細な変更点（関数単位の説明や未実装箇所の一覧）を追記できます。
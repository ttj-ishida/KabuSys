# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
重大なバグ修正や後方互換性のない変更は明確に記載しています。

## [Unreleased]

- ドキュメント・内部コメントの改善（コード理解性向上）。
- 監視・実行スクリプトのログ出力やエラーハンドリングを微修正（冪等性・運用耐性の向上）。
- small refactors / ロギングメッセージの改善。

---

## [0.1.0] - 2026-04-16

初回リリース。日本株自動売買フレームワークの基本機能を実装しました。以下は主な追加・変更点の概要です。

### Added
- 全体
  - パッケージ初期リリース（kabusys 0.1.0）。
  - プロジェクトの設定管理（kabusys.config.Settings）。
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - 各種環境変数（DB パス、API トークン、運用モード等）をプロパティとして提供。
  - バージョン定義: __version__ = "0.1.0"。

- 実行・運用用スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、スレッドでのエンジン実行、停止フラグ検出による安全停止。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 停止フラグ検出、例外時のログ出力、DB 初期化（監視テーブル）を行う。

- 監視・レポート
  - monitoring_db.init_monitoring_db の呼び出しを通じ監視テーブルの冪等初期化を実装（監視と実行で利用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して標準出力にレポートを出力。
    - コマンドラインから期間指定 (--from / --to) と DB パス (--db) を受け付け。

- ポートフォリオ構築（portfolio）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全てが 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限処理（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジームは警告ログの上でフォールバック。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）、単元株（lot_size）丸め、per-position/aggregate 上限、コストバッファの考慮、スケールダウンと残余配分ロジックを実装。

- Research（ファクター計算・解析）
  - research/factor_research.py
    - momentum, volatility, value ファクター計算（DuckDB を用いた SQL ベース実装）。
    - スキャン範囲や欠損ハンドリングを明示的に実装（ウィンドウ不足時に None を返す等）。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージエクスポートを実装（zscore_normalize を含む）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI (gpt-4o-mini) でスコアリングし、ai_scores テーブルへ書き込む処理を実装（スケルトン含む）。
    - ニュース収集ウィンドウ計算（calc_news_window）、バッチ処理、トークン過負荷対策、リトライ戦略、レスポンスバリデーション方針、スコアクリップを定義。
    - API キーの注入（引数または環境変数 OPENAI_API_KEY）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows 優先度クラス）設定ユーティリティ（set_process_priority）。
    - CPU Affinity 設定ユーティリティ（set_cpu_affinity）。
    - 未対応 OS や権限不足の際は警告ログでスキップ（安全設計）。

### Changed
- .env 読み込みロジック
  - export KEY=... 形式のサポート、クォートされた値のバックスラッシュエスケープ処理、インラインコメントの扱い改善を実装。
  - OS 環境変数（既存環境）を protected として .env.local からの上書きを制御する動作を導入。

- DB 周り
  - DuckDB と SQLite を併存利用する設計（分析用に DuckDB、操作ログ等に SQLite を使用）。

- 実行/監視の起動時挙動
  - 起動時にプロセス優先度を最初に設定するように変更（高優先度での安定稼働を優先）。

### Fixed
- 環境変数パースの堅牢性向上
  - MONITOR_POLL_INTERVAL の 0 以下や不正値を検出してデフォルトにフォールバックするよう修正（警告ログを出力）。
  - .env のパースでクォートやエスケープ、インラインコメントに起因する誤った値読み取りを修正。

- 配分・スケーリングの安定化
  - calc_score_weights の全スコア 0 のケースで等金額配分にフォールバックするよう修正（警告ログあり）。
  - calc_position_sizes の aggregate cap でのスケールダウン後に残余キャッシュを使って lot_size 単位で追加配分するロジックを実装し、より保守的で再現性のある割当てを保証。

- レジーム乗数の安全化
  - calc_regime_multiplier で未知レジーム時に 1.0 でフォールバックし、警告を出力するように修正。

- 監視ループの堅牢性
  - SystemMonitor.check_once() 内での予期しない例外をループ単位で捕捉して単一ポーリング失敗がプロセス全体を停止させないように変更。
  - 停止フラグ（data/stop_requested.flag）検出による安全な終了実装。

### Security
- 環境変数の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によってテストや CI で明示的に無効化可能。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的なエラーを発生させる（不正利用防止）。

### Notes / Known issues
- ai/news_nlp.score_news の実装はエラーハンドリングや最終書き込み処理を含むが、大量データや API レート制限下での運用は監視が必要（指数バックオフ・部分成功時のデータ保護方針は記載あり）。
- position_sizing の lot_size は現状グローバル定義（全銘柄共通）。将来的に銘柄別 lot_map を受け取る拡張を予定（コメントあり）。
- price を取得できない銘柄に関しては一部箇所で 0.0 を用いるため、エクスポージャーが過小見積もられる可能性あり（apply_sector_cap の TODO）。

---

この CHANGELOG はソースコードから仕様・振る舞いを推測して作成しています。実際の差分履歴（git commit）に基づく厳密な変更履歴ではありません。必要であればコミット履歴に基づく詳細な CHANGELOG（著者・コミットID・変更日の明記）を生成しますのでお知らせください。
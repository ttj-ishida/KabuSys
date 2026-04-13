# Changelog

すべての変更は Keep a Changelog の形式に準拠します。
なお、本ファイルは与えられたコードベースの内容から推測して作成した要約です。

※バージョン番号はパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせています。

## [Unreleased]

（現時点のスナップショットに基づく差分はありません。次リリースへ向けた追加・修正をここに記載してください。）

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーション構成・エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して実行を本番 DB と分離。起動時にプロセス優先度を設定し、ExecutionEngine を起動してセッションを実行する。
- 設定管理
  - config.py: 環境変数 / .env ロード機構を実装。プロジェクトルートの自動検出（.git / pyproject.toml を基準）、.env/.env.local の読み込みルール（OS 環境変数保護、override の挙動）、export プレフィックスやクォート値、コメント解析に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。Settings クラスで各種設定値をプロパティとして提供（DB パス、PID ファイル、閾値、環境判定など）およびバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）。
- ポートフォリオ構築（純関数群）
  - portfolio_builder.py: シグナル選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装（スコア全0 の場合のフォールバック含む）。
  - risk_adjustment.py: セクター集中制限を行う apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（regime のフォールバック挙動を含む）。
  - position_sizing.py: 発注株数決定ロジック calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）、単元株丸め、1銘柄上限・aggregate cap のスケールダウン、cost_buffer による保守的見積りなどを対応。
- 研究（Research）モジュール
  - research.factor_research: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）。prices_daily / raw_financials テーブルのみ参照する設計。MA200、ATR、各種リターン等の計算を SQL で実装。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク関数などを実装（外部依存なし）。
  - research.__init__ で zscore_normalize などの公開関数を束ねる。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI (gpt-4o-mini) へ送信して銘柄ごとのセンチメント ai_score を生成・ai_scores に書き込む処理を実装。記事集約、チャンク送信（最大 20 銘柄/リクエスト）、記事/文字数トリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分書き換え（DELETE → INSERT）で部分失敗時に他銘柄データを保護する設計。ターゲット日指定（target_date）によりルックアヘッドバイアスを防止。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定（high/normal/low）と CPU affinity 設定機能を提供。アクセス権限や未対応プラットフォームに対する警告・例外ハンドリングを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。コマンドライン引数 (--from, --to, --db) に対応。system_status / trade_logs / risk_logs などから稼働率・注文件数・成功率・送信率・レイテンシ（平均/最大/P95）などを集計し、閾値に基づく PASS/FAIL 判定を行う。P95 の計算や日付フィルタ、DB 存在チェックを備える。
- パッケージ情報
  - kabusys.__init__.py: パッケージ名と初期バージョン (0.1.0) を定義。

### Changed
- （初版のため特に既存機能の互換性を壊す変更はなし）

### Fixed / Robustness improvements
- 設定 / 入力バリデーションの強化
  - MONITOR_POLL_INTERVAL のパース時に負または不正値を検出した場合にログ警告を出してデフォルトにフォールバックするようにした（run_monitoring）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を行い、不正な値は ValueError で検出する（config.Settings）。
  - .env ファイルパーサで引用符付き値・エスケープ・インラインコメントの扱いを実装し、export プレフィックスに対応（config._parse_env_line）。
- DB 周りの安全策
  - run_execution / run_monitoring 起動時に Monitoring 用テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。
  - tools/paper_verification_report は存在しないテーブルに対して sqlite3.OperationalError を捕捉してデフォルト値を返す（堅牢化）。
- AI モジュールのフェイルセーフ
  - OpenAI API キー未設定時に明示的なエラーを出す（ai.news_nlp.score_news）。
  - API 呼び出し失敗時はログ出力・リトライを行い、それでも失敗した場合はスキップして処理を継続する方針（フェイルセーフ）。

### Notes / Usage
- 起動
  - 監視ループ: python -m kabusys.run_monitoring または run_monitoring.py を直接実行
  - 実行エンジン: python -m kabusys.run_execution
  - Paper 検証: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数（主要）
  - KABUSYS_ENV: development | paper_trading | live
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - OPENAI_API_KEY: ai/news_nlp での OpenAI キー
  - PAPER_FILL_MODE: instant | partial | never | reject
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1）

### Known limitations / TODOs (明示)
- position_sizing.calc_position_sizes:
  - lot_size を全銘柄共通としている（将来は銘柄別 lot_map への拡張を検討）。
  - price が欠損（0.0）の場合のエクスポージャー算出で過少見積りとなる可能性があり、前日終値等のフォールバックを検討中（risk_adjustment.apply_sector_cap のコメント参照）。
- ai/news_nlp.py: 大規模処理や API レート制限・エラー時の部分スループットについては現状のリトライ方針で対応しているが、運用に合わせたキューイングやバックプレッシャーの追加を検討推奨。

---

本 CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノート作成時は担当者による追加説明・影響範囲（マイグレーション手順、互換性注意点など）を補記してください。
Keep a Changelog 準拠 — 変更履歴 (日本語)
=====================================

すべての重要な変更はここに記録します。フォーマットは Keep a Changelog に準拠しています。セマンティックバージョニングを採用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。BrokerClientFactory を介して実ブローカー／モックを切替え、RiskManager / OrderManager / Reconciler を組み立ててセッションを実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はログ出力のうえデフォルト 60 秒にフォールバック）。監視は環境に依らず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml 基準）を実装。export プレフィックス、クォート／エスケープ、インラインコメント処理に対応した独自パーサを実装。.env / .env.local の読み込み順序と OS 環境変数の保護（上書き防止）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを公開。各種環境変数からの値取得・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。DB パスや監視関連パス、閾値などをプロパティで取得可能。
- モニタリング DB 初期化ユーティリティを参照・呼び出すコードを追加（init_monitoring_db 呼び出し）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ(--from/--to)、DB パス指定(--db) に対応。稼働率、注文成功率、送信率、レイテンシ(P95) 等の指標を集計し PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等配分・スコア加重の重み計算を実装。
  - portfolio/risk_adjustment.py: セクター上限適用ロジック（apply_sector_cap）、市場レジームによる乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、cost_buffer の考慮などを実装。
  - portfolio/__init__.py で主要関数をエクスポート。
- リサーチ／特徴量モジュール
  - research/factor_research.py: モメンタム、ボラティリティ、バリュー系ファクター（mom_1m/3m/6m、MA200 乖離、ATR20、avg_turnover、per、roe 等）を DuckDB 上で計算する関数を実装。データ不足時は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman rank）計算、ファクター統計サマリ等を実装。外部ライブラリ依存なしで実装。
  - research/__init__.py で主要関数と zscore_normalize を公開。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news から銘柄別に記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む機能を追加。バッチ処理（最大 20 銘柄／回）、トークン肥大対策（記事数・文字数上限）、429/ネットワーク/5xx の指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアのクリップ、部分成功時の置換戦略（DELETE→INSERT の限定実行）などの安全対策を実装。
  - calc_news_window により JST ウィンドウ（前日 15:00 ～ 当日 08:30）→ UTC 変換での抽出範囲を計算。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。set_cpu_affinity で CPU affinity の固定もサポート。アクセス権限不足等の失敗は警告ログで安全にフォールバック。
  - utils/__init__.py を追加（パッケージ化準備）。

Changed
- DB ハンドリング・分離
  - 実行系は paper_trading 環境時に paper_trading 用 SQLite を利用して本番監視 DB と完全に分離するよう設計（settings.is_paper 判定）。
- 環境変数ロードの挙動
  - .env の読み込みルールを明確化（.env.local は .env を上書き）。OS 環境変数は保護され上書きされない仕組みを導入。
- ログ・エラーハンドリング
  - run_monitoring/run_execution 等の起動スクリプトで初期にプロセス優先度設定を行い、各種例外はログ記録してループ継続や安全終了を行う実装に。

Fixed
- .env パーサの堅牢性向上
  - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどを実装し、より実用的な .env パーシングを行うよう改善。
- 環境変数値のバリデーション
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対して警告を出しデフォルトへフォールバックするロジックを追加。

Security
- OpenAI API キーの取り扱い
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出し誤動作を防止。

Notes / Implementation details
- DuckDB / SQLite の使い分け:
  - 分析系（prices_daily, raw_financials, ai_scores 等）は DuckDB を想定。運用監視・取引ログは SQLite（monitoring.db / paper_trading.db）を使用。
- 設計方針:
  - 研究・解析系関数は副作用を持たない純粋関数として実装（ユニットテストしやすさ重視）。
  - 実行系は外部 API（ブローカー）アクセス部を抽象化し切替可能に設計（BrokerClientFactory）。
  - 主要箇所で「データ不足時は None を返す」「例外はログに出してフェイルセーフで続行する」方針を採用。

今後の予定（例）
- ユニットテスト補充（特に position_sizing のスケールダウンロジック、news_nlp のレスポンスバリデーション）。
- stocks マスタに単元株情報を持たせ、銘柄別 lot_size 対応を有効化。
- ai/news_nlp の並列化と API コスト最適化（キャッシング等）。

--- 

この CHANGELOG はソースコードの実装内容から推測して作成しています。補足・修正希望があれば差分に合わせて更新します。
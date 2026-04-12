CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
現在のバージョンは src/kabusys/__init__.py に定義された v0.1.0 です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性に注意）
- Fixed: バグ修正
- Security: セキュリティ修正や注意点

Unreleased
----------

（なし — 必要に応じてここに今後の変更を記載してください）

[0.1.0] - 2026-04-12
--------------------

Added
- コア実行 / 監視
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合に専用の paper_trading DB を使用し、MockBrokerClient を利用して本番 DB と完全に分離する動作をサポート。
    - 実行開始時にプロセス優先度を設定するフックを導入（utils/process_priority.set_process_priority）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。

- 設定管理
  - config.py: 環境変数・.env ファイル読み込み・Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env 行パーサ（クォート・エスケープ・コメント処理）を実装。
    - override/protected の仕組みで OS 環境変数を上書きから保護。
    - 各種設定プロパティ（DB パス、API トークン、監視閾値、ペーパー取引設定など）を提供。PAPER_FILL_MODE の検証など。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定と等重・スコア加重の重み計算を追加（select_candidates / calc_equal_weights / calc_score_weights）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを追加（risk_based / equal / score の配分方式、lot_size・cost_buffer の扱い、aggregate cap によるスケール調整）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに対する乗数（calc_regime_multiplier）を追加。

- リサーチ / ファクター
  - research/factor_research.py: モメンタム / ボラティリティ / バリュー系ファクター計算を実装（DuckDB 接続を受け prices_daily/raw_financials を参照）。
    - calc_momentum, calc_volatility, calc_value を提供。データ不足時の None ハンドリングあり。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリーを実装。
    - calc_forward_returns, calc_ic, rank, factor_summary を提供。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。

- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI API でセンチメントスコア化して ai_scores に書き込む機能を追加。
    - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）。
    - 銘柄ごとに記事を集約し、トークン肥大対策（記事数/文字数トリム）。
    - 最大 20 銘柄/バッチでの API 送信、JSON Mode を想定したレスポンスバリデーション、スコアクリッピング。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ (再試行) を組み込み。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定（Windows / POSIX）と CPU affinity 設定関数を追加。
    - 権限不足や未対応プラットフォーム時は警告ログを出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - コマンドライン引数 (--from, --to, --db) に対応。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等の集計と PASS/FAIL 判定（閾値付き）を出力。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を呼んで監視テーブルの存在を保つ（冪等に初期化）。

Changed
- デフォルト / 動作方針
  - run_execution: paper_trading 環境では paper_sqlite_path を使用して本番データと分離する設計を採用。
  - run_monitoring: 監視用プロセスは環境に依存せず本番 sqlite_path を参照する旨を明文化（監視データは一元化）。
  - config: .env の読み込み順序は OS 環境 > .env.local > .env、.env.local は override=True で優先して適用。ただし OS の既存環境変数は保護される。

Fixed
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ対応やインラインコメントの扱いを改善し、無効行のスキップを明確化。
- ポートフォリオ / position sizing の端数処理
  - lot_size 単位での切り捨て・残余配分のアルゴリズムを実装（スケールダウン時の再配分ロジックを明記）。
- research モジュールの数値ハンドリング
  - データ不足により算出不能な場合は None を返し、呼び出し側が安全に扱えるように仕様を統一。

Security
- 環境変数の扱いに注意
  - .env 自動ロードは便利だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 環境変数は protected として上書きされない設計。

Notes / Known limitations
- 一部機能は外部モジュール（SystemMonitor, ExecutionEngine, BrokerClientFactory, など）の実装に依存しており、本 changelog は現時点で提供されているモジュール群の API 仕様から推測して記載しています。
- ai/news_nlp の OpenAI 呼び出しは外部 API に依存するため、API のレスポンス形式やレート制限により挙動が変わる可能性があります。実運用時は OPENAI_API_KEY の管理と API コストに注意してください。
- portfolio の価格参照で price が欠損（0.0）の場合、現在は単にスキップ／過少見積りとなるため将来的に前日終値等のフォールバック導入が推奨されています（コード内に TODO 記載）。

著者注
- 本 CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のリリース履歴やコミットメッセージとは差異があり得ます。必要であれば差分やコミット履歴を参照して正確な履歴を反映します。
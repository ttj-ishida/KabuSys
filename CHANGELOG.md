CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-12
------------------

Added
- 初回リリース。
- 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）にデータを記録して本番 DB と完全分離する。
    - 実行前にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - DuckDB を分析用に併用（duckdb ファイル: data/kabusys.duckdb）。
    - OrderRepository、OrderManager、RiskManager、Reconciler 等を組み合わせてセッション実行を行う。
    - RiskManager のデフォルト設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）を組み込み。
- 監視
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告してデフォルトにフォールバックする。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を High に設定。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env / .env.local 自動ロード機能（プロジェクトルート自動探索: .git または pyproject.toml を基準）。
    - OS 環境変数保護（.env の上書き制御、.env.local は上書き可）。
    - 必須環境変数検査ヘルパー、各種設定プロパティ（PATH、PID ファイル、閾値、環境種別など）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - コマンドライン実行可能（--from, --to, --db 引数対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う（閾値はソース内定義）。
    - DB が存在しない場合のエラーメッセージ、各種テーブル欠如時のフォールバック処理を実装。
- ポートフォリオ構築
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークに signal_rank 使用）
    - calc_equal_weights / calc_score_weights（スコア合計 0 の場合は等金額配分へフォールバック）
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクターエクスポージャーに基づく候補除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた投下多寡を調整。unknown は 1.0 にフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート
    - lot_size（単元株）対応、単元切り捨て・スケールダウン・残余配分ロジックを実装
    - aggregate cap（available_cash）を超える場合のスケール処理と安全弁（max_per_stock）を実装
    - cost_buffer による保守的見積りをサポート
- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB 上で計算する関数を提供。
    - データ不足時の None ハンドリングやウィンドウスキャン範囲最適化を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリーを提供。
    - pandas 等を使わずに標準ライブラリのみで実装。
  - パッケージエクスポートを追加（src/kabusys/research/__init__.py）。
- ニュース NLP（AI）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチで送信して銘柄ごとのスコアを ai_scores に書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）とそれに基づく記事抽出を実装。
    - バッチサイズ、文字数制限、記事数制限、スコアクリップ（±1.0）を実装。
    - API エラー（429、タイムアウト、5xx、ネットワーク断）に対する指数バックオフリトライ。部分失敗時に既存スコアを保護する DB 書き込み戦略。
    - OpenAI API キー未設定時は ValueError を投げる明示的チェック。
- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - 権限不足や未対応環境では警告してスキップする安全設計。

Changed
- パッケージメタ情報として __version__="0.1.0" を設定（src/kabusys/__init__.py）。

Fixed
- 環境変数読み込み
  - .env パーサはクォート内のエスケープとインラインコメント挙動に対応し、export KEY=val 形式もサポート。
  - .env の上書き制御と protected keys により OS 環境変数が誤って上書きされないようにした。
- モニタリング
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合に警告してデフォルトへフォールバックするよう改善。
- calc_score_weights
  - 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に供給する設計。未設定時は例外を発生させることで誤った動作を防止。

Notes
- デフォルトのデータファイルパス
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid
- 環境変数の自動読み込みはプロジェクトルートが検出できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が指定された場合は無効化されます。
- DuckDB を用いたファクター計算は prices_daily / raw_financials テーブルを前提としています。production 用 DB 構成に合わせてテーブルを用意してください。

Deprecated
- なし

Removed
- なし

（注）本 CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合があります。
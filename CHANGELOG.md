CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリース。KabuSys の基本機能一式を追加。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を使用する設計を用意。
      - 実行中は execution.pid を使用して PID 管理、data/stop_requested.flag による外部停止フラグをサポート。
      - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててスレッドでセッション実行。
      - RiskConfig のデフォルト値（max_position_pct 等）を定義。initial_portfolio_value は broker.get_available_cash() から動的に初期化。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
      - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番 DB に記録する設計）。
      - data/stop_requested.flag によるループ終了、KeyboardInterrupt での終了処理を実装。
  - 設定管理
    - config.py: Settings クラスを導入し、環境変数 / .env の読み込み・検証を実装。  
      - プロジェクトルート検出（.git または pyproject.toml を探索）に基づき自動で .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
      - .env パーサは export 形式、クォート、インラインコメント等に対応。
      - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別等）。環境変数のバリデーションを行う（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
      - settings 変数をモジュールレベルでエクスポート。
  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder: シグナル選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア全0時は等配分にフォールバックして警告。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限の適用）と calc_regime_multiplier（市場レジームに応じた資金乗数）を実装。unknown セクター扱い、レジーム不明時のフォールバック動作を明記。
    - portfolio.position_sizing: calc_position_sizes による発注株数決定ロジックを実装。  
      - risk_based / equal / score の配分方法をサポート。lot_size（単元株）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer（手数料・スリッページ推定）などを考慮。
      - スケールダウン時の残差取り扱いや再配分ロジックを実装して再現性を確保。
  - リサーチ（DuckDB ベースのファクター計算）
    - research.factor_research: Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を追加。prices_daily / raw_financials テーブルを参照し、欠損・データ不足時の扱いを明示。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を追加。外部依存は使わず標準ライブラリのみで実装。
    - research.__init__ に主要 API をエクスポート（z-score 正規化は data.stats から利用）。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。  
      - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL 判定（閾値はソース内定数）を表示。
      - DB パスはコマンドライン --db / 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
  - AI ニュース NLP（骨格実装）
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングして ai_scores に書き込む処理の設計・主要ロジックを実装。  
      - ニュース収集ウィンドウ（JST ベースを UTC に変換）やバッチサイズ、トークン肥大化対策、API リトライ戦略、レスポンスバリデーション、スコアのクリップ、部分置換（DELETE→INSERT）による堅牢な DB 書き込みを検討済み。  
      - 実装ドキュメント内で DuckDB executemany の注意点等も明記。
  - ユーティリティ
    - utils.process_priority: プロセス優先度設定（Windows / POSIX 差分吸収）と CPU affinity 固定ユーティリティを追加。アクセス権限不足や未サポート環境では警告ログを出して安全にスキップする設計。

Changed
- なし（初期リリースのため「追加」が中心）。

Fixed
- なし（初期リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし（現状、API キーなどは環境変数で取り扱う旨をドキュメント化。OpenAI API キー未設定時は明示的なエラーを発生させる実装）。

Notes / Breaking changes
- 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する点に注意。監視データを paper_trading DB から分離したい場合は本設定を見直す必要あり。
- .env の自動読み込みはプロジェクトルートの検出 ロジックに依存する（.git または pyproject.toml を基準）。パッケージ配布後や特殊な配置では自動ロードがスキップされる可能性あり。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- ai.news_nlp は堅牢性を考慮した設計で主要ロジックを備えているが、実行系（OpenAI との具体的な呼び出しループ処理・DB 書き込みの完全な流れ）はソース末尾で途中（切れている）ため、デプロイ前に最終実装とテストが必要。

開発者向けメモ
- Settings._require は必須環境変数未設定時に ValueError を送出。CI/デプロイ環境では .env を適切に用意すること。
- position_sizing の lot_size は将来的に銘柄別対応に拡張予定（TODO をソースに記載）。
- DuckDB へ executemany などで空パラメータを渡すとエラーになるため、ai.news_nlp では事前にパラメータ非空を確認している。

---  
メンテナンス: 将来のリリースでは以下を検討してください。  
- ai.news_nlp の最終実装と詳細なテスト（API エラーシミュレーション・部分失敗時の保護動作確認）  
- monitoring と execution の DB 分離ポリシーの明文化（運用上の期待動作とデフォルトの整合性確認）  
- portfolio モジュールの単体テスト拡充（スケールダウンや lot 単位の端数処理などの境界ケース）
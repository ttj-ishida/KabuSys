# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
日付はソースコードの最終更新推定日として 2026-04-13 を使用しています。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本パッケージ情報を追加
  - kabusys.__version__ = "0.1.0" を導入。

- 環境設定・ロード機能
  - kabusys.config.Settings クラスを追加。環境変数経由で設定値を提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 等）。
  - .env / .env.local 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサーは export プレフィックスの対応、引用符内のバックスラッシュエスケープ、行末のインラインコメント処理などに対応し堅牢化。

- 実行用スクリプト
  - run_monitoring.py を追加：SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する（意図的な動作）。
  - run_execution.py を追加：ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と完全分離。

- 監視 DB 初期化
  - init_monitoring_db を用いた監視テーブル初期化処理を run_* スクリプトで行う（冪等動作）。

- プロセス制御ユーティリティ
  - kabusys.utils.process_priority を追加。Windows / POSIX (Linux, macOS, FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定、CPU affinity を最初の N コアに固定する機能を提供。権限不足や未対応 OS 時は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。
  - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
  - portfolio.position_sizing: 発注株数計算 (calc_position_sizes) を実装。risk_based / equal / score の割当方式に対応し、単元株丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮する。

- リサーチ機能（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算関数を実装（prices_daily / raw_financials を参照）。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman ρ）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク変換 (rank) を提供。
  - DuckDB 接続を受け取り SQL と Python のハイブリッドで計算。営業日ベースのウィンドウ、欠損値の扱い、ウィンドウサイズ閾値のチェック等を含む。

- AI / ニュース NLP スコアリング
  - ai.news_nlp モジュールを追加。raw_news と news_symbols を集約し OpenAI (gpt-4o-mini) へバッチ送信して銘柄別センチメントスコアを ai_scores テーブルへ書き込むパイプラインを実装。
  - バッチサイズ、最大記事数／文字数トリム、JSON モード期待、429/5xx/ネットワークエラーに対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ置換）などのフェイルセーフ設計を採用。
  - calc_news_window: ターゲット日のニュース収集ウィンドウ（JST→UTC 変換）を提供。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を計算して標準出力にレポートを出力。閾値（例: 稼働率 >=99%）や P95 計算、日付フィルタ (--from / --to)、DB パスの CLI オプションをサポート。

### 変更 (Changed)
- 起動時のプロセス優先度をデフォルトで "high" に設定する処理を run_monitoring.py / run_execution.py の先頭で行うようにした（パフォーマンス安定化目的）。
- run_monitoring の挙動を明示：
  - 監視用 DB は KABUSYS_ENV に依らず settings.sqlite_path（本番パス）を使用する仕様に明文化。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB とデータを分離する動作を明確化。

### 修正 (Fixed)
- .env パーサーの挙動改善
  - export プレフィックス、引用符内のエスケープ、インラインコメントの検出を正しく処理するようにし、誤ったパースによる設定漏れを防止。
- position_sizing / risk_adjustment における価格欠損に対するログ出力を追加し、価格が無い銘柄をスキップする安全弁を導入。
- research モジュールの SQL においてウィンドウ内データ不足時に None を返すように修正（不完全データでの誤計算を防止）。

### セキュリティ (Security)
- 必須環境変数取得時（_require）に未設定の場合 ValueError を送出する実装により、実行前に明示的に設定漏れを検知するようにした（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。

### 既知の制約 / 注意点 (Known issues / Notes)
- ai.news_nlp は OpenAI API キー（OPENAI_API_KEY）を前提とし、キー未設定時は ValueError を送出する。API 使用時にレイテンシ課金やレート制限を考慮する必要あり。
- position_sizing の price 欠損時に現状は単純にスキップする実装。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残している。
- apply_sector_cap は sector_map に無い銘柄を "unknown" として上限チェックから除外するため、マスタデータの未整備があるとセクター制限が正しく機能しない可能性がある。
- MONITOR_POLL_INTERVAL に不正値（非正整数や 0 以下）が設定された場合はデフォルト 60 秒へフォールバックし、警告ログを出す。

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

---

開発・運用上の補足:
- DuckDB と SQLite を併用する設計（分析用 DuckDB、状態 / 監視 / 発注ログ等は SQLite）を採用しています。バックアップやファイルパスの設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）は運用時に確認してください。
- 本 CHANGELOG はソースコードからの推測に基づく初期リリース記録です。追加のコミット履歴や実際のリリースノートが存在する場合は、そちらに合わせて更新してください。
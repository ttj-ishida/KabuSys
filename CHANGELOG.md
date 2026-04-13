# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現在のスナップショットは初回リリース相当の内容を含むため、下の 0.1.0 を参照してください）

## [0.1.0] - 2026-04-13

初回公開リリース。本リリースでは自動売買システム KabuSys のコア機能群（実行・監視・ポートフォリオ構築・リサーチ・NLP スコアリング・ユーティリティ等）を実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/`.env` 読み込みと一元管理機能を追加。`.env` と `.env.local` の自動読み込み（プロジェクトルート検出あり）をサポート。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサを実装（コメント、export 形式、クォートおよびバックスラッシュエスケープ対応、インラインコメントの扱いなど）。

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient（モック実装）を使用し、paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 実行開始時にプロセス優先度を "high" に設定。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動するエントリポイントを提供。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec など）を明示的に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト: 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用する設計。

- データベース / 分析
  - DuckDB と組み合わせたリサーチモジュールを追加。
    - research.factor_research: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials テーブル参照）。
    - research.feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、ファクターの統計サマリー、rank ユーティリティ。
    - DuckDB 接続を受け取り SQL＋純粋関数で計算する設計（外部 API に依存しない）。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates（スコア順ソート、タイブレークルールあり）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分へフォールバック）
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター別エクスポージャーを計算し上限超過セクターの候補を除外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。

- NLP / AI
  - ai.news_nlp:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルに書き込む機能を追加。
    - チャンク単位（最大 20 銘柄/リクエスト）での送信、トークン肥大化対策（1銘柄あたり最大記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング実装。
    - ニュース収集ウィンドウの計算ユーティリティ（JST ベースで前日 15:00 〜 当日 08:30 相当を UTC 変換）を提供。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。期間フィルタ（--from/--to）と DB パス指定（--db）をサポート。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定（閾値はソース内で定義）を出力。
    - P95 計算、SQL クエリの堅牢化（テーブルが存在しない場合の例外処理）を実装。

- ユーティリティ
  - utils.process_priority:
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows の HIGH_PRIORITY_CLASS、POSIX の nice 値に対応）。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を追加。
    - 権限不足や未対応 OS へは警告を出して安全にスキップ。

### Changed
- 設計上の注意 / 動作仕様
  - 環境変数/設定の扱いを厳密化：
    - Settings のプロパティで各種値（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）のバリデーションを行うようにした（無効値では ValueError を送出）。
    - .env の読み込み順序を OS 環境変数 > .env.local > .env と明確に定義し、OS 環境変数は保護（上書き不可）する。
  - run_monitoring の既定ポーリング間隔や監視 DB の扱い（本番 sqlite_path を使用）を明確化。

### Fixed
- 安定性・入力バリデーションの改善
  - MONITOR_POLL_INTERVAL の不正（非整数・0・負数）を検出してデフォルト（60 秒）へフォールバックし、警告ログを出すようにした（run_monitoring）。
  - PAPER_FILL_MODE の不正値を検出して ValueError を投げるようにした（Settings）。
  - .env ファイル読み込み時のファイルアクセス失敗は警告に留めて処理継続するようにし、テスト/実行中の致命的障害を回避（Settings）。
  - process_priority の未対応 OS / 権限不足時に警告ログを出してスキップするようにし、起動失敗を防止。
  - tools.paper_verification_report で DB ファイルが存在しない場合のエラーメッセージを分かりやすく出力し処理を中断。
  - research/feature_exploration の calc_forward_returns で horizons の検証を追加（正の整数かつ最大 252 日まで）。

### Security
- 今回のリリースではセキュリティ修正は含まれていません。API キーや機密情報は Settings 経由で環境変数により与える設計。OpenAI API キー未設定時は明示的に ValueError を raise して処理を中断します（ai.news_nlp）。

---

今後の予定（例）
- ExecutionEngine の永続化チェックポイント、より詳細な監視メトリクスの収集。
- portfolio モジュールのテストカバレッジ拡充、lot_size の銘柄別対応。
- ai.news_nlp の失敗時ロギング強化と部分リトライ戦略の改善。

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴やプロジェクト管理上の変更履歴とは異なる場合があります。
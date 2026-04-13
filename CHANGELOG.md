# Changelog

すべての重要な変更点をここに記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正・堅牢化
- Security: セキュリティ/機密情報に関する変更

※以下はリポジトリ内のコード構成・実装内容から推測して作成しています。

## [0.1.0] - 2026-04-13
初回リリース。KabuSys のコア機能群（監視・実行・ポートフォリオ構築・リサーチ・ツール・ユーティリティ・AI ニューススコアリング）を実装。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は本番の sqlite_path を使用する実装。
  - run_execution.py: 実売買/ペーパートレード双方に対応した ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離する。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート判定：.git / pyproject.toml）、.env/.env.local の優先度制御、export 形式・クォート・エスケープ・インラインコメント対応など堅牢なパーサーを実装。各種設定プロパティ（DB パス、PID/kill フラグ、しきい値、環境判定、PAPER_FILL_MODE バリデーション等）を提供。
- 監視周り
  - monitoring_db の初期化呼び出しを両エントリポイントで実行し、監視テーブルの存在を保証（冪等）。
  - duckdb を併用するための接続確立処理を追加。
- 実行周り（Execution）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を想定）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立てと実行（RiskManager にデフォルト設定を提供し、初期ポートフォリオ値に broker.get_available_cash() を使用）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限（既存保有を考慮した候補フィルタ）、レジームに応じた資金乗数（bull/neutral/bear のマップ）。
  - portfolio.position_sizing: 複数配分方式（risk_based / equal / score）に対応した株数算出、単元株丸め（lot_size）、max position/aggregate cap、cost_buffer による保守的見積りとスケールダウンロジックを実装。
- リサーチ
  - research.factor_research: DuckDB を用いた定量ファクター計算（モメンタム、ボラティリティ、バリュー）。ウィンドウ関数・集計・欠損ハンドリングを含む。
  - research.feature_exploration: 将来リターン計算（任意 horizon の一括取得）、Spearman ランク相関（IC）計算、rank/統計サマリー関数を実装。外部ライブラリに依存しない実装。
  - research.__init__: 公開 API に必要な関数群をエクスポート（zscore_normalize は data.stats から利用）。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を実装。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。日付フィルタ・DB パス指定に対応。
- AI / ニュース NLP
  - ai.news_nlp: raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。バッチ（最大 20 銘柄）送信、記事/文字数トリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分失敗時のデータ保護（コード単位で削除→挿入）などを備える。
- ユーティリティ
  - utils.process_priority: Windows/Linux/macOS を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。psutil 例外をハンドリングして失敗時は警告でスキップする実装。

### Changed
- 監視用 DB の動作方針: run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を監視用 DB として使用する設計（監視は常に本番状態を監視するため）。
- run_execution: paper_trading の場合は settings.is_paper により paper_sqlite_path を使用して本番 DB と分離する挙動を明確化。
- DB 接続のクローズ処理を finally で保証（sqlite3/duckdb の両方）。

### Fixed / Robustness
- .env パーサーの堅牢化: export 形式、クォート内のバックスラッシュエスケープ、インラインコメント対応、不正行のスキップなど細かな挙動を改善。
- MONITOR_POLL_INTERVAL の値検証を追加。1 未満（0 や負数）や非整数の指定は警告してデフォルト（60 秒）にフォールバックするよう変更。
- Paper trading 用処理で監視テーブルが存在しない場合でも init_monitoring_db を呼ぶことで冪等にテーブルを用意するようにした。
- AI スコアリング: OpenAI API キー未設定時は明示的な ValueError を発生させる、API コールの失敗はリトライ/ログでハンドリングして全処理を止めない設計。

### Security
- OpenAI API の利用時に API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時はエラーとして明示。

### Documentation / Developer notes
- パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
- 各モジュールに設計方針や注記（TODO 等）が含まれており、将来的な拡張ポイント（銘柄ごとの lot_size マスタ導入、価格フォールバック、DuckDB executemany の制約への対応等）が明記されている。

---

今後の想定（コードからの推測）
- 単体テスト追加、CI ワークフロー整備
- ストラテジーやブローカークライアントのモック実装強化
- 手数料/スリッページモデルの明確化（cost_buffer の拡張）
- DuckDB のスキーマ整備・マイグレーション機能
- AI スコアリングの結果検証用テスト・ロギングの強化

（必要であれば、この CHANGELOG をもっと細かいリリース履歴（例: 0.1.0 → 0.1.1 など）に分割して作成します。どの程度の粒度がよいか指示してください。）
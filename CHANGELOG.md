# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※以下はソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 実行系
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - BrokerClientFactory により実環境/ペーパートレードを切り替え可能。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - Engine を別スレッドで実行し、data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
    - 実行 PID を data/execution.pid に記録する運用をサポート（Engine 側）。
- 監視系
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - data/stop_requested.flag による停止検出、例外発生時のログ保護、接続クローズ処理を実装。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
- 設定 / 環境変数管理
  - config.py：環境変数・.env の自動読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づく .env/.env.local の自動ロード（OS 環境変数が優先）。
    - export KEY=val 形式、クォート/エスケープ、インラインコメントの扱いに対応する .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - Settings クラスで各種設定値（J-Quants / kabu / LINE / DB パス / pid/kill フラグ /監視しきい値 / env/log_level 等）をプロパティとして提供。必須変数は未設定時に ValueError を送出。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- ポートフォリオ構築
  - portfolio.portfolio_builder：銘柄選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出力。
  - portfolio.position_sizing：株数決定ロジック（calc_position_sizes）。
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、最大ポジション/総投入資金（max_position_pct / max_utilization）制約、コストバッファを考慮した集約スケーリング、スケール時の端数分配アルゴリズムを実装。
  - portfolio.risk_adjustment：セクター集中上限適用（apply_sector_cap）および市場レジームに基づく乗数（calc_regime_multiplier）。
    - apply_sector_cap は既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" にマップし、未知レジームは 1.0 へフォールバック（警告ログ）。
- 研究/分析
  - research.factor_research：DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）。
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルのみ参照。
  - research.feature_exploration：将来リターン計算・IC 計算・統計サマリ。
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）、rank（平均ランク付け）を実装。
  - research パッケージ __init__ で zscore_normalize を kabusys.data.stats から再公開。
- ツール
  - tools.paper_verification_report.py：Paper Trading の検証レポート生成ツールを追加。
    - DB（デフォルト data/paper_trading.db）からシステム稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）をサポート。テーブル未存在時に sqlite3.OperationalError を捕捉して安全にレポートを生成。
- AI / ニュース NLP（下敷き）
  - ai.news_nlp.py：raw_news を OpenAI API でスコアリングして ai_scores に書き込むモジュールを追加（実装設計を含む）。設計上の特徴：
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）定義、銘柄ごと集約、記事数/文字数上限、バッチ処理、JSON Mode 想定、再試行（指数バックオフ）、レスポンス検証、スコアのクリップ、部分更新による耐障害性など。
    - score_news, calc_news_window 等のユーティリティを実装（ファイル末尾で未完の箇所あり）。

- ユーティリティ
  - utils.process_priority：クロスプラットフォームなプロセス優先度設定 set_process_priority と CPU affinity 設定 set_cpu_affinity を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、アクセス権限不足や未対応 OS の場合は警告ログでスキップ。

### Changed
- .env の読み込み仕様を明確化
  - 自動ロードの対象ファイル順序: OS 環境 > .env.local > .env（.env.local は上書き）。既存の OS 環境変数は保護される。
- 監視・実行起動時のプロセス優先度設定を起動直後に行うよう統一（set_process_priority("high")）。
- run_monitoring / run_execution が duckdb と sqlite の接続確保・初期化（init_monitoring_db）を行うようにして、監視テーブルの存在を冪等に保証。

### Fixed
- 環境変数パーサーの改良
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、より頑健に .env を読み込めるように修正。
- calc_score_weights: 全スコアが 0.0 の場合に 0 除算や不正な重み配分が発生しないよう等金額配分へフォールバック（警告ログ）。
- calc_position_sizes:
  - 単元丸め・上限処理や aggregate cap スケーリングでの端数配分ロジックを実装し、利用可能現金を超過しないように調整。
- run_execution / run_monitoring:
  - data/stop_requested.flag を事前に検査し、不要な起動や中断を防止。
  - 予期せぬ例外発生時にループを止めずログ出力して次のポーリングまで待機する安全化（監視ループ）。

### Notes / 潜在的な影響（重要）
- 監視（run_monitoring）は「KABUSYS_ENV に関係なく本番 sqlite_path を使用する」実装になっています。テストやペーパートレード環境で監視 DB を分離したい場合は設定やコードの変更が必要です。
- Settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）は未設定だと起動時に ValueError を投げます。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD の利用や環境変数のモックを検討してください。
- ai/news_nlp.py は設計上概ね完成していますが、ファイル末尾で処理途中の箇所が存在します（ソースが途中で切れているため、実運用前に完全実装と動作確認が必要です）。
- set_process_priority / set_cpu_affinity はプラットフォームや権限によって動作しない場合があります（警告でスキップ）。

---

今後の改善候補（議論中）
- ai.news_nlp の完全実装とテスト（OpenAI API のレスポンス例を含む単体テスト）。
- monitoring 用に環境別の DB パスを選択できるオプション（現状は本番 DB 固定）。
- position_sizing の銘柄別 lot_size サポート（将来的に銘柄マスタから取得）。
- DuckDB クエリのパフォーマンスチューニングおよび大規模データに対するベンチマーク。

もし実際のコミット単位や追加の変更点（欠落しているモジュールやテストなど）を反映したい場合は、該当する差分/コミットログを提供してください。より正確な CHANGELOG を作成します。
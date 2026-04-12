Keep a Changelog — kabusys

すべての変更はセマンティックバージョニングに従います。  
このファイルはプロジェクトの主要な変更点を人間に読みやすく記録するためのものです。

フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-12

### 追加 (Added)
- 基本パッケージリリース（初回公開: 各モジュールのコア機能を実装）
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB（data/paper_trading.db 既定）を使用して本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを生成（MockBrokerClient 対応想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて実行セッションを開始。
    - 起動時にプロセス優先度を "high" に設定。
- 監視用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するスクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データの一元化）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理モジュール
  - config.py
    - .env / .env.local を自動で読み込み（プロジェクトルート判定: .git または pyproject.toml）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - .env パーサを実装（export 形式、クォート、インラインコメント処理、保護キー/override ロジック）。
    - 各種設定プロパティを提供（J-Quants / Kabu API / LINE / DB パス / 監視閾値 / システム環境等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - KABUSYS_ENV 値検査（development|paper_trading|live）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮、売却予定銘柄を除外可能）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。単元株（lot_size）で丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積りなどを実装。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用して、監視テーブルの存在を保証（冪等）。
- research（ファクター・リサーチ）
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB を用いた SQL ベースの計算）。
    - 長期 MA・ATR・出来高等のファクターを計算。欠損やデータ不足時に None を返す扱いを徹底。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン計算（任意ホライズン対応）。
    - calc_ic: スピアマンランク相関（IC）計算（ランク処理と ties の平均ランク処理を実装）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）。
    - rank ユーティリティ。
  - research パッケージは pandas 等に依存せず標準ライブラリ + duckdb で完結する設計。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む処理を実装。
    - バッチサイズ・文字数制限・記事数上限・スコアクリッピングなどを設定可能。
    - API エラー（429・ネットワーク・5xx 等）に対する指数バックオフリトライとフェイルセーフ（失敗しても処理継続）。
    - タイムウィンドウ計算（JST ベース -> UTC 変換）と出力 JSON 検証を実装。
- ユーティリティ
  - utils.process_priority
    - psutil を用いたプロセス優先度設定（Windows / POSIX の差分を吸収）。
    - set_cpu_affinity によりプロセスを最初の N コアに固定可能（アクセス権限がない場合は警告してスキップ）。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加（期間指定オプション --from/--to / --db）。
    - system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出。
    - PASS/FAIL 判定としきい値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）に基づく判定を出力。
- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として定義。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の注意点 / 実装上の設計コメント
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計（監視データの一元化）。開発環境で監視 DB を分離したい場合は環境変数を明示的に変更してください。
- .env ローダはプロジェクトルートの自動検出に __file__ を基点とするため、配布パッケージやテスト実行環境で動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- position_sizing の価格欠損（price が 0 または None）の扱いに関する TODO コメントあり（将来的にフォールバック価格導入を検討）。
- ai.news_nlp は OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。API レスポンスと料金を伴うため運用時に注意してください。
- set_process_priority / set_cpu_affinity は権限やプラットフォーム制約により無効化されることがあり、その場合はログに警告が出力され処理は継続します。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

今後の予定（例）
- テストカバレッジと CI の整備
- Broker / MockBroker の実装詳細とインタフェースの明確化
- ロギング設定の集中化（Settings.log_level の適用）
- position_sizing の銘柄別 lot_size 対応、価格フォールバック実装
- ai.news_nlp のレスポンス検証強化・メトリクス計測

（この CHANGELOG はコードベースから推測して作成しました。細かい挙動や追加の変更履歴は実際のコミットログを参照してください。）
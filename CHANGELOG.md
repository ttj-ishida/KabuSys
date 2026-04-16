# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のソースコードから推測して作成した初期の変更履歴です（自動生成ではなくコードの実装内容に基づく要約です）。

全般的な注記
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて v0.1.0 を初期リリースとしています。
- 日付は本 CHANGELOG 作成日（2026-04-16）を使用しています。

Unreleased
- （なし）

[0.1.0] - 2026-04-16
========================================
Added
- 基本アプリケーション・コンポーネントを実装（初期リリース）。
  - 実行系
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
      - KABUSYS_ENV=paper_trading の際は MockBroker を利用し、paper_trading 用の SQLite（data/paper_trading.db）へ記録して本番 DB と分離する設計。
      - BrokerClientFactory の利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモン化されたセッションスレッド実行と停止フラグ対応を実装。
      - 実行時の PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）をサポート。
  - 監視系
    - SystemMonitor のポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化する動作を明示。
      - プロセス優先度設定（High）を起動時に行うフローを採用。
  - 設定管理
    - 環境変数 / .env 自動ロード機能を実装（src/kabusys/config.py）。
      - プロジェクトルート（.git または pyproject.toml 基準）を探索して .env を読み込み、.env.local で上書き可能。
      - export KEY=...、クォート付き値（エスケープ考慮）、インラインコメント処理などをサポートするパーサを実装。
      - 各種設定プロパティ（DB パス、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証、監視閾値など）を提供。
  - ポートフォリオ構築（src/kabusys/portfolio/*）
    - 銘柄選定・重み計算（select_candidates、calc_equal_weights、calc_score_weights）
      - score 重みが全 zero の場合は等分配にフォールバックし WARNING を出力。
    - セクター制約・レジーム乗数（apply_sector_cap、calc_regime_multiplier）
      - セクター露出上限による候補除外、レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - ポジションサイズ計算（calc_position_sizes）
      - risk_based / equal / score の配分方式、単元（lot_size）丸め、個別・総合キャップ（max_position_pct / max_utilization）、コストバッファによる保守的見積り、スケールダウンと残差処理を実装。
  - リサーチ（src/kabusys/research/*）
    - ファクター計算（calc_momentum、calc_volatility、calc_value）：DuckDB を用いた prices_daily / raw_financials 参照の定量ファクターを実装。
    - 特徴量探索（calc_forward_returns、calc_ic、factor_summary、rank）：将来リターン算出、IC（Spearman 相関）計算、基本統計量を実装。
    - research パッケージのエクスポートを整備。
  - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news テーブルからニュースを集約し OpenAI（gpt-4o-mini）でセンチメントスコアを付与して ai_scores に書き込むワークフローを実装（バッチ処理、トークン肥大化対策、リトライ/バックオフ、レスポンス検証、スコアクリッピングなどを考慮）。
    - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供。
  - 便利ツール
    - Paper Trading 検証レポート生成 CLI（src/kabusys/tools/paper_verification_report.py）を追加。
      - システム稼働率・注文成功率・送信率・レイテンシ（P95）等を算出して標準出力に整形。
      - --from/--to/--db オプションと PAPER_TRADING_SQLITE_PATH 環境変数に対応。DB が見つからない場合のユーザ向けエラーメッセージを実装。
  - ユーティリティ
    - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。Windows/Linux(Mac含むPOSIX) を抽象化し、権限不足や未対応環境でのフォールバックを実装。

Changed
- デフォルト動作 / 設計上の決定を明確化
  - 監視プロセスは常に production 相当の sqlite_path を使用（KABUSYS_ENV によらない） — 監視データの一元化を意図。
  - Paper Trading は専用 SQLite（data/paper_trading.db）を使用し、本番データと明確に分離。
  - .env の読み込み順序は OS 環境 > .env.local > .env（.env.local が .env を上書き）。
  - MONITOR_POLL_INTERVAL の 0 以下や不正な文字列はデフォルト（60 秒）へフォールバックし、ログで警告。

Fixed
- 仮想的な不整合や境界条件の対策を追加・改善
  - calc_score_weights: 全スコア合計が 0.0 の場合に等金額配分へフォールバックして警告を出力。
  - .env パーサ: export 付き行やクォート内のエスケープ、インラインコメント処理を厳密化して意図しないトークン分割を防止。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値に対する例外回避とログ通知を追加。
  - tools.paper_verification_report: DB が存在しない場合にわかりやすいエラーメッセージを出力。
  - utils.process_priority: 未対応 OS や権限不足時に例外を握りつぶしてログ警告に切り替えることで起動失敗を防止。
  - research.rank: ランク計算の ties 検出を浮動小数の丸めで安定化。

Security
- 設定管理モジュールは必須の機密環境変数（例：JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）を _require() でチェックし、未設定時は ValueError を発生させて早期に失敗するように設計。

Notes / Known limitations
- AI ニュース NLP 周りは API 呼び出しや外部ネットワークに依存するため、API キー未設定時は明示的なエラーを発生させる実装。失敗時は個別処理をスキップして継続するフェイルセーフ設計が採られている。
- position_sizing の価格フォールバック（前日終値や取得原価）は TODO コメントとして残されており、価格欠損時の扱いに改善余地あり。
- 一部モジュール（例: ai.news_nlp の score_news の続きを含む部分）は大きな処理を伴うため実行時の外部依存性（OpenAI、DuckDB データ有無など）に注意が必要。
- DuckDB を利用するクエリは prices_daily/raw_financials 等のテーブル構造に依存するため、データ投入側のスキーマ互換性に注意。

========================================

今後の提案（参考）
- リリースごとに自動で CHANGELOG を更新するためのテンプレート化（GitHub Actions 等）を検討すると運用が楽になります。
- AI スコアリングのテストカバレッジ（モックを用いた単体テスト）を拡充すると本番切替時の安心感が高まります。
- position_sizing の lot_size を銘柄別に扱う拡張、価格フォールバック実装は優先度が高い改善候補です。
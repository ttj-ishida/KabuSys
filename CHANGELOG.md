# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。日付や変更点は、提供されたコードベースから推測した内容に基づき作成しています。

## [0.1.0] - 2026-04-16

概要: 初期リリース相当の機能群を実装。自動売買エンジンの実行・監視周り、ポートフォリオ構築、リサーチ／ファクター計算、ニュースNLP スコアリング、ユーティリティ、および検証ツールを含みます。データ層は SQLite（監視／paper_trading）および DuckDB を使用する設計です。

### 追加 (Added)
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - DuckDB と SQLite を組み合わせた分析／永続化基盤を採用（duckdb_path / sqlite_path の設定）。

- 実行・エンジン
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - BrokerClientFactory により環境（本番 / paper_trading）に応じたブローカークライアントを生成。
    - Paper Trading（KABUSYS_ENV=paper_trading）では専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - PID ファイル書き込みサポート（data/execution.pid を想定）。
    - リスク管理パラメータのデフォルト（RiskConfig）を実装し、初期ポートフォリオ値を broker.get_available_cash() から取得。

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず監視は本番 sqlite_path を参照して監視テーブルを更新（監視用 DB の初期化）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt による終了もハンドリング。
    - プロセス優先度を起動時に高優先度に設定。

- コンフィグ / 環境読み込み
  - config.py:
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数を保護して .env.local で上書き可能）。
    - .env パーサを実装（export 形式、クォート文字列、インラインコメント考慮、無効行スキップ）。
    - Settings クラスを導入し、各種環境変数をプロパティで提供（J-Quants / kabu API / LINE / DB / 監視閾値 / システム環境 等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH、閾値（CPU/MEM/DISK）などを定義。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中上限適用（apply_sector_cap）、市場レジームに基づく投下倍率（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py:
    - 単元株丸め、人為的なリスクベース／等配分ロジック（calc_position_sizes）を実装。
    - aggregate cap に基づくスケーリングと残余配分のロジックを実装。
  - portfolio パッケージのエクスポート設定を追加。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）計算関数を実装。DuckDB 接続を受け取り SQL ベースで計算。
  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、rank、統計サマリー（factor_summary）を実装。
  - research/__init__.py に主要 API を公開。

- ニュース NLP（AI）
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む処理を追加（バッチ送信、スコアクリップ、レスポンス検証、部分更新戦略）。
    - ニュース収集ウィンドウ計算（calc_news_window）を実装（JST 指定 → UTC に変換）。
    - API キー解決、リトライ（指数バックオフ）方針、トークン肥大対策（記事数・文字数の制限）を実装。
    - フェイルセーフの設計（API 失敗時はスキップし続行）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、基準値（閾値）を設定して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、テーブル存在チェックを実装。

- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差分を吸収してプロセス優先度設定（set_process_priority）を実装（Windows / POSIX 対応）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を追加。
    - 権限不足や未サポート時は警告ログを出し安全にスキップ。

### 変更 (Changed)
- 監視周りの運用方針（設計上の注意）
  - run_monitoring が常に本番用 sqlite_path を使用する仕様を採用（KABUSYS_ENV に依存しない監視 DB 利用）。これは監視データの一元化を意図した仕様。

- DB 初期化
  - init_monitoring_db() を run_execution/run_monitoring の起動時に呼び出し、監視テーブルの存在を冪等的に保証。

- .env の自動読み込みルール
  - OS 環境変数（既存値）を保護しつつ .env/.env.local を読み込む挙動を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。

### 修正 (Fixed)
- ロバスト性強化
  - env パーサでクォート付き値のバックスラッシュエスケープやインラインコメントを正しく扱うよう改善。
  - run_monitoring の MONITOR_POLL_INTERVAL 読み取りで不正値（0以下・非整数）に対するフォールバックと警告ログを追加（time.sleep で ValueError を避ける）。
  - run_execution/run_monitoring で接続を finally で閉じることでリソースリークを防止。
  - position sizing / risk adjustment 等で価格欠損時のログ出力やスキップ処理を追加し、安全性を向上。

### 注意点 / 既知の制約 (Known Issues)
- ai/news_nlp.py は API キー未設定時に ValueError を送出する設計（外部でキー提供が必須）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だと sector_exposure が過小見積りされる可能性があり、将来的に前日終値や取得原価をフォールバックする TODO がコメントとして残されている。
- DuckDB executemany の制約を考慮した実装（空パラメータを回避）を意図しているが、部分的な失敗時のロールバック戦略は限定的。
- set_cpu_affinity / set_process_priority は権限不足や未対応 OS の場合はスキップし、完全な動作を保証しない（警告ログを出力）。

### セキュリティ (Security)
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は Settings で明示的に require し、未設定時は例外を送出して安全性を高める設計。

---

今後の改善候補（抜粋）
- position_sizing の銘柄毎 lot_size を stocks マスタで持たせる拡張。
- ai/news_nlp の部分失敗時のリトライ・ロギング改善や並列処理最適化。
- monitoring / execution のユニットテストと統合テストの整備（stop フラグや PID 管理等の E2E テスト）。
- .env の読み込みに関するより厳密なユニットテスト（特殊文字・エスケープケース）。

（以上）
# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを想定しています。

現在のバージョン指標はパッケージ内の __version__ 値 (0.1.0) に合わせて初回リリースを作成しています。  
（コード内容から推測した機能・設計や未実装箇所についても注記しています。）

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本アーキテクチャ・起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理はプロジェクトの production sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を分離して使用（data/paper_trading.db を想定）。停止フラグ（data/stop_requested.flag）と PID ファイルの扱いを実装。
- 設定・環境読み込み
  - config.py: Settings クラスを追加し、環境変数から各種設定を取得。自動でプロジェクトルートの .env/.env.local を読み込む機能（OS 環境変数を保護）を実装。クォート・エスケープ・インラインコメント対応の .env パーサを実装。
  - 環境変数の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）とデフォルト値を提供。
- 監視・実行周り
  - monitoring_db 初期化呼び出しの統合（起動時に必要テーブルが存在するよう冪等で初期化）。
  - 停止フラグ検出、例外ハンドリング、接続後の確実なクローズ処理を実装。
- Portfolio モジュール（ポートフォリオ構築）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を実装（スコア全ゼロ時は等分配にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装（既知レジーム: bull/neutral/bear）。
  - portfolio.position_sizing: 単元株丸め、risk_based / equal / score の allocation_method に対応した株数決定ロジック、集約キャップ（available_cash）を超えた際のスケールダウンと残差処理を実装。lot_size や cost_buffer を考慮。
- リサーチ（Research）モジュール
  - research.factor_research: DuckDB 接続を用いたファクター計算を実装（モメンタム / ボラティリティ / バリュー）。prices_daily / raw_financials テーブルのみ参照する設計。
  - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計要約(factor_summary) とランク関数(rank) を実装。外部ライブラリに依存しない純 Python 実装。
  - research パッケージが zscore_normalize を外部（kabusys.data.stats）からエクスポート。
- AI ニュース NLP
  - ai.news_nlp: raw_news を集約して OpenAI API (gpt-4o-mini) でセンチメントを算出し、ai_scores テーブルへ書き込むワークフローを実装。バッチ処理、トークン肥大化対策（記事数・文字数制限）、スコアクリッピング、リトライ（エクスポネンシャルバックオフ）などを設計。
  - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ算出）を提供。
  - OpenAI API キー無しの場合は明示的にエラーを返す実装。
  - （注）news_nlp のソースは途中で切れており、一部処理（記事フェッチや DB 書き込みの最終実装）は未完／作業中。
- ユーティリティ
  - utils.process_priority: Windows/POSIX の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足や未対応環境では警告でスキップするフェイルセーフ設計。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などを集計し、閾値判定（PASS/FAIL）を行う。--from/--to/--db オプションに対応。
- パッケージ情報
  - __init__.py にてパッケージ名とバージョン（0.1.0）を設定。

### 変更 (Changed)
- DB の扱い
  - Monitoring は起動時に KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する設計に明示（run_monitoring）。一方、実行エンジンは paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離（run_execution）。
- 環境変数読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で自動ロード。既存 OS 環境変数は保護される。
- エラーハンドリング
  - run_monitoring のチェックループ内で check_once() の例外をキャッチしてログ出力し、ループは継続する安全性を確保。
  - .env ファイル読み込みでの読み込み失敗は warnings.warn による柔軟な扱いに変更。

### 修正 (Fixed)
- 環境変数の整合性チェック
  - MONITOR_POLL_INTERVAL の値を整数かつ正の数に検証し、不正値時はデフォルトにフォールバックして警告を出すよう改善（run_monitoring）。
  - PAPER_FILL_MODE の許容値チェックを追加（instant/partial/never/reject）。不正値は ValueError。
  - KABUSYS_ENV / LOG_LEVEL の不正な値は ValueError を送出して早期検出するようにした（Settings）。
- リソースクリーンアップ
  - run_monitoring/run_execution で sqlite3/duckdb の接続を finally にて確実にクローズするように修正。

### セキュリティ (Security)
- OpenAI API キーの扱いは明示的で、未設定時は失敗（ValueError）して誤動作を防止。

### 既知の問題・作業中 (Known issues / WIP)
- ai/news_nlp.py の実装が途中で切れており、記事取得処理 (_fetch_articles 等) や DB への置換ロジックの完全な実装は未完。API リクエストのレスポンス検証や DB 書き込みのトランザクショナル保護は設計として記載されているが、実装の最終確認が必要。
- portfolio.risk_adjustment.apply_sector_cap の価格欠損（price_map に 0.0 または欠損）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価フォールバックの実装を検討すべき。
- position_sizing のロジックは lot_size が全銘柄共通で固定（現状 100 単元想定）。将来的には銘柄別 lot_size 対応の拡張を予定。

---

将来のリリースでは以下を想定しています（実装優先度メモ）:
- ai.news_nlp の完全実装（記事集約、OpenAI 部分の堅牢化、DuckDB 書き込みのトランザクション化）
- Portfolio 周りの単元別対応や価格フォールバック処理
- テストカバレッジの追加（特に資金配分・スケールダウンロジック）
- 実行エンジン / リスクマネージャー周辺の統合テストとフェイルオーバー改善

---

参考: この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
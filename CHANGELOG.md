# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付は本ファイル生成日（2026-04-17）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
### 追加 (Added)
- 初回リリース。
- 実行用スクリプト / デーモン類
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の際は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた安全な起動／停止制御を実装。
    - RiskManager にデフォルトの RiskConfig 値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値入力時はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、init_monitoring_db() でテーブル存在を保証。
    - 停止フラグ検知によりループ終了、KeyboardInterrupt による正常終了処理。
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などの集計を行い、PASS/FAIL 判定を出力。
    - コマンドライン引数 --from / --to / --db に対応。DB が存在しない場合にわかりやすいエラーメッセージを表示。
    - DB テーブルが存在しない（OperationalError）場合にフォールバックして処理を継続する堅牢化。
- 設定・環境変数管理
  - config.py: .env 自動ロード機能を実装（.env, .env.local の順、OS 環境変数を保護）。  
    - _find_project_root() により __file__ を基点にプロジェクトルートを探索（.git または pyproject.toml を検出）。
    - .env パース処理の強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理（クォート無し時の '#' 扱い）などに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - Settings クラスを導入し、環境変数の必須チェック（_require）および各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 閾値系など）を提供。環境値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を追加（スコアが全て 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限の適用）、calc_regime_multiplier（市場レジームに基づく投下資金乗数）を追加。未知レジームは警告とともに 1.0 フォールバック。
  - portfolio.position_sizing: calc_position_sizes を追加。  
    - risk_based / equal / score 各方式に対応。単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差を考慮した追加配分ロジックを実装。
    - 価格欠損時のログ出力や安全弁を実装。将来的拡張の TODO コメントあり（銘柄別 lot_size 等）。
- 研究・リサーチモジュール
  - research.factor_research: DuckDB を用いたファクター計算を実装（Momentum / Volatility / Value）。  
    - calc_momentum, calc_volatility, calc_value を提供。200日移動平均やATR、出来高/売買代金等を計算。
  - research.feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク付け（rank）を実装。  
    - 外部ライブラリに依存せず標準ライブラリのみで実装。horizons の検証や ties の処理（平均ランク）に配慮。
  - research.__init__: 既存ユーティリティ（zscore_normalize）との統合をエクスポート。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）で解析し ai_scores テーブルへ書き込む処理の骨格を追加。  
    - ニュース収集ウィンドウ計算（calc_news_window）、API バッチ送信（最大 20 銘柄）、JSON モード出力の強制、スコアクリッピング、リトライ（429/ネットワーク/5xx）と指数バックオフを仕様として記載。
    - 実装は堅牢性（バリデーション、部分失敗時の既存スコア保護）を考慮。
- ユーティリティ
  - utils.process_priority: set_process_priority（Windows / POSIX 対応）と set_cpu_affinity（最初の N コアへピン留め）を追加。  
    - 未対応 OS の場合は警告を出してスキップ。権限不足などの例外は警告により安全にフォールバック。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- なし（初回リリースのため該当なし）

### 注意事項 (Notes)
- Settings の一部プロパティは環境変数未設定時に ValueError を送出するため、デプロイ前に必須変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を .env に設定してください。
- .env の自動ロードはプロジェクトルートを基準に行うため、パッケージ配布後や CWD が異なる状態でも正しく動作するよう設計されています。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp のスコアリングフローは API キー（OPENAI_API_KEY）を必要とします。キー未設定時は例外が発生します。
- ai.news_nlp の処理は本ファイルに全文が含まれていない箇所があります（途中で切れている実装あり）。運用前に残りの処理（記事フェッチ・API 呼び出し・DB 書き込み等）が実装されていることを確認してください。
- DuckDB / SQLite へのテーブル名やスキーマは本コードの SQL に依存します。既存 DB と合わせて移行してください。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元対応の拡張を予定しています（TODO コメントあり）。

---

今後のリリースでは以下を想定しています:
- ai.news_nlp の完全実装と統合テスト
- モニタリング・リスク管理周りの拡張（アラート送信、kill/clear フロー）
- 銘柄別 lot_size 対応、および portfolio モジュールの追加チューニング
- DuckDB クエリのパフォーマンス最適化と大規模データ向けチューニング

（必要であれば、この CHANGELOG をプロジェクトの実際の変更履歴に合わせて追記・修正します。）
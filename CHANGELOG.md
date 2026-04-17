CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容（ソースから推測できる実装・設計方針）に基づいて変更点・リリース内容を日本語で記載しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: 追加（Added）/ 変更（Changed）/ 修正（Fixed）/ 非推奨（Deprecated）/ 削除（Removed）/ セキュリティ（Security）

Unreleased
----------
- （今後の計画・改善点をここに記載）

[0.1.0] - 2026-04-17
--------------------
Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
- 実行系:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。設定に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用することで本番 DB と分離する挙動を実装。
  - BrokerClientFactory を使用したブローカークライアント生成の統合。
  - ExecutionEngine の起動/停止ループをスレッドで実行し、data/stop_requested.flag による外部停止検知、実行 PID ファイル出力対応（data/execution.pid）を実装。
  - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - OrderManager / OrderRepository / Reconciler の連携を組み込み、発注フローの基盤を実装。

- 監視系:
  - run_monitoring.py: SystemMonitor をポーリングする監視ループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する設計。
  - 監視起動時にプロセス優先度を「high」に設定する処理を組み込み（utils/process_priority.set_process_priority を使用）。
  - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定/環境ロード:
  - config.py: 環境変数読み込みユーティリティを追加。プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みする仕組みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ: export プレフィックス対応、クォート内のバックスラッシュエスケープ、行内コメント処理など堅牢なパース実装を導入。
  - Settings クラスに各種プロパティを追加（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、データベースパス、PID/KILL フラグ関連、閾値設定、env/log_level バリデーションなど）。
  - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）を実装。
  - PAPER_TRADING_SQLITE_PATH 環境変数で paper_trading DB のパスを上書き可能。

- データ解析 / ポートフォリオ構築:
  - portfolio モジュールを実装:
    - portfolio_builder: 信号選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を提供。スコア全てがゼロの場合のフォールバック警告を追加。
    - risk_adjustment: セクター集中制限を施す apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバックして 1.0 を返す（警告ログあり）。
    - position_sizing: 発注株数算出 calc_position_sizes を実装（risk_based / equal / score の allocation_method、lot_size 丸め、単銘柄上限・集計上限のスケーリング、cost_buffer を考慮した保守的見積り、残差に基づく追加配分アルゴリズム）。
  - モジュールのエクスポートを __init__ で整理。

- リサーチ / 特徴量:
  - research モジュールを実装:
    - factor_research: DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）。各ファクターはデータ不足時に None を扱う設計（ウィンドウ不足での安全な処理）。
    - feature_exploration: 将来リターン計算 calc_forward_returns、IC（calc_ic）、factor_summary、rank 関数を追加。外部依存（pandas 等）を使わず標準ライブラリと DuckDB で完結する設計。
    - zscore_normalize を data.stats から再公開。

- AI / ニュース NLP（下流処理基盤）
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込むための設計を実装（ニュースウィンドウ計算、記事集約、バッチ送信、リトライ・バックオフ、レスポンス検証、スコアクリップ、部分置換によるデータ保護など）。（ファイル終端が途中で切れているため一部実装は継続予定と推測）

- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。CLI (--from, --to, --db) を提供し、期間フィルタ・システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。P95 計算、日付フィルタ生成、DB 存在チェック・例外回避を実装。閾値はソース内で定義（稼働率 99%、注文成功率 90% 等）。

- ユーティリティ:
  - utils/process_priority.py: cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）、および CPU affinity 固定（set_cpu_affinity）を実装。権限不足や未対応 OS に対しては警告ログを出してスキップするフェイルセーフを実装。

Changed
- ロギングとフェイルセーフの強化:
  - 各所で logging を用いた情報/警告/例外出力を追加し、外部 API 失敗やデータ欠損時にサービス全体が停止しない設計へ。

Fixed
- N/A（初期リリースのため既知のバグ修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する仕様。未設定時はエラーを投げることで誤使用を防止。

注意事項 / マイグレーションメモ
- 環境変数の自動ロード:
  - デフォルトでプロジェクトルートにある .env / .env.local が読み込まれます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING と本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視（run_monitoring）は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使用する点に注意してください。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。不正な値（整数変換不可や 0 以下）はデフォルト 60 秒にフォールバックして警告ログを出します。
- PAPER_FILL_MODE:
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかのみ有効。設定ミスは ValueError を投げます。
- プロセス優先度 / CPU affinity:
  - set_process_priority / set_cpu_affinity は権限やプラットフォームにより実行できない場合があるため、その場合はログで警告してスキップします。

開発者向けメモ
- ai/news_nlp.py は設計が詳細に書かれているが、ファイル末尾が途中で切れているため実装の続きを行う必要があります（記事フェッチ関数や API 呼び出しループなど）。
- テストコードは本リリースで含まれていないため、ユニットテスト/統合テストの追加を推奨します（特に position_sizing のスケーリングロジックや news_nlp の API リトライ処理）。
- 将来的には lot_size を銘柄別に扱えるよう stocks マスタの導入を検討する旨の TODO コメントあり。

補足
- 本 CHANGELOG はソースコードから推測した実装内容・設計意図に基づき作成しています。実際のコミット履歴や外部ドキュメントと差異がある可能性があります。
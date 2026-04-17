# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

<!-- 例: 新しいリリースを追加する場合は日付を更新してください -->

## [0.1.0] - 2026-04-17

初回リリース。本リリースでは自動売買システムのコア機能群（起動スクリプト、設定読み込み、ポートフォリオ構築、ポジションサイズ計算、リスク制御、研究用ファクター計算、ニュースNLPスコアリング、各種ユーティリティおよび検証ツール）を実装しました。

### 追加 (Added)
- パッケージ情報
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) 検知で安全に停止。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB (data/paper_trading.db) に記録して本番 DB と完全分離。
    - 停止フラグおよび PID 管理 (data/execution.pid) に対応。
    - スレッド実行と安全な停止処理を実装。
- 設定管理
  - config.py
    - .env/.env.local の自動読み込み（プロジェクトルートが検出できる場合。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 独自の .env パーサ（export プレフィックス、クォート・エスケープ、インラインコメント対応）。
    - Settings クラスを導入し、各種設定（DB パス、API トークン、監視閾値、環境判定、paper_trading 用設定等）をプロパティとして提供。
    - 各種入力バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプト（期間指定可）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算して判定（PASS/FAIL）。
    - DB のテーブル欠損やデータ不足時のフォールバック処理を実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順、同点時は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等金額配分にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中制限。既存保有のセクター比率を計算して候補を除外）。
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数: bull/neutral/bear 対応、未知値は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、max_position_pct 上限、aggregate cap（available_cash に収まるようスケール＆残差配分）などを実装。
    - cost_buffer による保守的コスト見積もりをサポート。
- リサーチ（研究用）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB を用いた SQL+Python 実装）。
    - MOMENTUM / MA200 / ATR / 流動性指標などを計算。
  - research/feature_exploration.py
    - calc_forward_returns（複数ホライズンに対応）、calc_ic（Spearmanランク相関）、factor_summary、rank。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。
- AI / NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとに ai_scores テーブルへ書き込む処理設計を実装（バッチ、トリミング、リトライ、レスポンス検証、±1.0 クリップ等）。
    - ニュース取得ウィンドウ計算 utility（calc_news_window）を実装。
    - OpenAI API キー解決（引数 > 環境変数）、失敗時は例外を送出。
    - （注）ファイル末尾の処理が一部切れている箇所があり、score_news 内の続き実装が必要（詳細は「既知の問題」参照）。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority（Windows / POSIX 差分を吸収して優先度を設定、失敗時は警告してスキップ）。
    - set_cpu_affinity（最初の N コアに固定するユーティリティ、権限不足時は警告してスキップ）。
- パッケージエクスポート
  - portfolio や research モジュールの __init__ で主要関数を公開。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）。

### 修正 (Fixed)
- 環境値の検証を強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検知してデフォルトにフォールバックするメッセージを追加。
  - PAPER_FILL_MODE の有効値チェックを追加（instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックを追加。
- DB 接続・初期化
  - 起動時に監視用テーブルの存在を保証する init_monitoring_db の呼び出しを実装（冪等）。
  - paper_trading 環境では paper_trading 専用 sqlite を使用（settings.paper_sqlite_path）。
- 安全性・堅牢化
  - run_execution のスレッド制御により停止フラグ検知で安全停止。
  - set_process_priority / set_cpu_affinity は権限不足や未サポート環境で安全にスキップするように変更。
  - paper_verification_report: DB のテーブルが存在しない場合の例外ハンドリングを追加して、レポート生成が中断しないようにした。

### 既知の問題 (Known issues)
- ai/news_nlp.py の実装がファイル末尾で切れており、score_news の記事集約および API 呼び出し以降の処理が未完です。OpenAI 呼び出しから ai_scores テーブルへの書き込みロジックは設計済みですが、現状では未完成で動作しません。完了実装が必要です。
- position_sizing の price フォールバックロジック（価格欠損時の扱い）は TODO コメントあり。price が 0.0 の場合にエクスポージャーの過少見積りが生じる可能性があります。
- DuckDB 操作に関してはバージョン依存（executemany の制約など）に注意が必要。paper_verification_report 内に互換性に関する注意点を残しています。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env.local は .env の上書き、ただし OS 環境変数は保護されます。
- 重要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須（未設定時は例外）。
  - OPENAI_API_KEY: ai/news_nlp の実行に必須（未設定時は例外）。
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（正の整数、デフォルト 60）。
  - PAPER_FILL_MODE: paper_trading の Fill 動作（instant|partial|never|reject）。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）。
  - DUCKDB_PATH / SQLITE_PATH: デフォルトは data/kabusys.duckdb / data/monitoring.db。
- 実行管理
  - 監視・実行プロセスは data/stop_requested.flag を置くことで外部から停止できます。
  - run_execution は PID を data/execution.pid に書きます（設定により変更可能）。
  - プロセス優先度設定は起動直後に High に変更が試みられます（権限がない場合は警告のみ）。

---

将来的な改善案（予定・提案）
- ai/news_nlp.score_news の未完成部分の実装完了（バッチ処理、レスポンス検証、部分更新ロジック）。
- position_sizing の価格フォールバック（前日終値や取得原価の使用）実装。
- 銘柄ごとの lot_size を管理するためのマスタ実装（銘柄別単元サポート）。
- DuckDB 操作のテストカバレッジ拡充と互換性検証。

（以上）
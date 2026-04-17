# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17

### 追加
- 全体
  - 初回リリース。ライブラリ/アプリケーションの基本コンポーネントを実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行 / 監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を最初に "high" に設定する仕組みを組み込み。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) による停止制御。
    - 依存コンポーネントの組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）。
    - RiskManager にデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec 等）を追加し、初期ポートフォリオ値を broker.get_available_cash() から取得。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（Monitoring 用 DB は本番 DB を参照する仕様）。
    - 停止フラグ (data/stop_requested.flag) によりループ停止。例外はログ出力して次ポーリングへ継続。

  - monitoring_db 初期化呼び出しを両スクリプトで行い、監視テーブルの存在を保証（冪等）。

- 設定 / 環境変数関連
  - config.py: 環境変数 / .env 読み込み・パース機能を実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（__file__ を基点にするため CWD に依存しない）。
    - .env / .env.local 自動ロード（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効にするためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env 行パーサーは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - 環境変数取得をラップする `Settings` クラスを実装。多数のプロパティを追加:
      - API トークン / パスワード（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）
      - DB パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH）
      - PID/kill flag パス、kill flag の起動時クリア設定
      - 監視閾値（CPU/MEM/DISK）
      - PAPER_FILL_MODE（paper trading の挙動）に対するバリデーション（有効値: "instant"、"partial"、"never"、"reject"）
      - KABUSYS_ENV, LOG_LEVEL の値検証（許容値チェック）
      - helper プロパティ: is_live / is_paper / is_dev

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - CLI で期間（--from, --to）と DB パス（--db）を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。
    - システム稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計して判定（PASS/FAIL）を出力。
    - デフォルトの合格基準値を定義（稼働率>=99%、fill rate>=90%、send rate>=95%、P95<=200ms）。
    - DB にテーブルがない場合のフォールバック（OperationalError を補足して N/A 扱い）。

- ポートフォリオ構築 (portfolio)
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア降順＋signal_rank によるタイブレーク）
    - calc_equal_weights（等分配）
    - calc_score_weights（スコア比率で重み付け、全スコアが 0 の場合は等分配へフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（既存保有を考慮したセクター上限チェック。sell_codes を除外して算出。unknown セクターは制限対象外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバック）
  - portfolio/position_sizing.py:
    - calc_position_sizes（allocation_method = risk_based / equal / score をサポート）
    - lot_size 単位で丸め、per-position 上限と aggregate 上限（available_cash）を考慮
    - cost_buffer（手数料・スリッページ見積り）を加味した安全なスケーリングロジック
    - スケールダウン時の端数処理で残余キャッシュを活用するアルゴリズムを実装

  - portfolio/__init__.py で主要関数群をエクスポート。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を追加。Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収して nice / priority を設定し、権限・未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) を追加。利用可能なコア数に合わせてプロセスの CPU affinity を設定。引数検証と失敗時の安全処理あり。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum（1/3/6 か月リターン、MA200 乖離を DuckDB 上の SQL で計算）
    - calc_volatility（20日 ATR、ATR pct、20日平均売買代金、volume_ratio を計算）
    - calc_value（最新財務データ（raw_financials）と価格から PER/ROE を計算）
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する純粋関数群として実装
  - research/feature_exploration.py:
    - calc_forward_returns（horizons 指定可能、複数ホライズンをまとめて高速取得）
    - calc_ic（スピアマンのランク相関を直接算出して IC を返す。レコード不足時は None）
    - rank（平均ランク（ties を平均ランクで処理））
    - factor_summary（count/mean/std/min/max/median を計算）
  - research/__init__.py にて主要関数群をエクスポート（zscore_normalize は data.stats からインポート）。

- AI / ニュース NLP（部分実装）
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）へ送って銘柄毎のセンチメントを算出し ai_scores テーブルへ書き込む設計を実装。
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する calc_news_window。
    - バッチ送信（1 回あたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ等の方針を実装。
    - 出力形式やレスポンス検証、部分置換による DB への安全な書き込み戦略を設計に含む。
    - （注）ファイルは途中まで実装されており、score_news の処理がソースファイル末端で途切れているため（切れている箇所あり）完全実装は次バージョンで補完予定。

### 変更
- なし（初回リリースのため既存コードの後方互換性に影響する大きな変更はなし）。

### 修正
- なし（新規実装中心）。

### 削除
- なし。

### 既知の注意点 / 互換性と設計上の決定
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用」する設計。監視データを paper_trading DB と分離したい場合は運用側で明示的に sqlite_path を切り替える必要があります。
- config.Settings のプロパティは不正な値を渡すと ValueError を送出する（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。運用時に .env の記載を確認してください。
- ai/news_nlp.py は大枠が実装されていますが、ソースの終端で処理が途切れているため（部分実装）、本機能を運用で利用する前に未完了箇所の実装確認が必要です。
- process_priority の設定は権限やプラットフォームによって失敗する可能性があり、その場合は警告ログを出して安全にスキップします。

### セキュリティ
- このリリースでの特記すべきセキュリティ修正はありません。環境変数や API キー（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は適切に保護してください。

---

今後の予定（例）
- ai/news_nlp の残実装（記事取得・OpenAI リクエスト/レスポンス処理・DB 書き込み）を完了して次バージョンへ。
- テストカバレッジの拡充と CLI/運用ドキュメントの整備。
- portfolio の lot_size を銘柄別に指定できるよう拡張。
# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
フォーマット: 重大度の高い変更はカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）に分類しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-13

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として追加（src/kabusys/__init__.py）。
  - 環境変数・設定読み込み機能（src/kabusys/config.py）を追加。.env 自動ロード機能、.env/.env.local の読み込み順序、OS 環境変数の保護機構を備えます。
    - プロジェクトルートの検出は .git または pyproject.toml を探索して行うため、CWD に依存しません。
    - .env のパースは export 句・クォート・エスケープ・インラインコメント対応を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - Settings クラスに多数のプロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, cpu/memory/disk 閾値, env/log_level 判定など）。
    - PAPER_FILL_MODE 等の設定値は妥当性検査を行い、不正値は ValueError を投げる。

- 実行スクリプト
  - 実運用向け監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を初期化し、ポーリングループで定期チェックを実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告後デフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
  - 実取引／ペーパートレード用実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を用いて DB を完全分離（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory を用いたブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の run_session 実行を行う。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しによる監視用テーブルの冪等な初期化を実行（run_monitoring/run_execution で使用）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収したインターフェースを提供。
    - set_process_priority(level: "high"|"normal"|"low")：アクセス権限エラー等は警告でスキップ。
    - set_cpu_affinity(cpu_count: int | None)：指定が None の場合は何もしない。利用不可・権限不足は警告でスキップ。

- Portfolio 構築
  - ポートフォリオ構築関連モジュールを追加（src/kabusys/portfolio/）。
    - portfolio_builder:
      - select_candidates: スコア降順（同点は signal_rank 小さい方優先）で上位 N を選択。
      - calc_equal_weights: 等比率配分。
      - calc_score_weights: スコア比率で重み計算。全スコアが 0 の場合は等配分にフォールバック（WARNING）。
    - risk_adjustment:
      - apply_sector_cap: セクターごとの既存エクスポージャーに基づき、新規候補を除外（unknown セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下倍率を返す。未知レジームは警告の上で 1.0 にフォールバック。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて株数を算出。単元株（lot_size）丸め・per-stock 上限・aggregate cap（available_cash に基づくスケーリング）を実装。cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究（Research）
  - factor_research（src/kabusys/research/factor_research.py）を追加：
    - calc_momentum / calc_volatility / calc_value：DuckDB 接続を受け取り SQL ベースで各種ファクター（モメンタム、ATR、出来高・売買代金、PER/ROE 等）を計算。
    - 各関数はデータ不足時に None を返す仕様やウィンドウ計算の詳細を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）を追加：
    - calc_forward_returns：将来リターン（複数ホライズン）を計算。horizons の妥当性検査を実装。
    - calc_ic：スピアマンランク相関（IC）を計算。有効レコード数が 3 未満なら None を返す。
    - rank / factor_summary：ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __init__ で主要 API をエクスポート。

- AI ニュース NLP
  - src/kabusys/ai/news_nlp.py を追加：
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む処理を実装。
    - 処理はバッチ（最大 20 銘柄）で API 呼び出し、リトライ（429/ネットワーク/5xx に対する指数バックオフ、最大リトライ回数設定）を行う。
    - 出力 JSON のバリデーション、スコアの ±1.0 クリップ、DB への安全な部分更新（対象コードのみ置換）等のフェイルセーフを備える。
    - ニュース収集ウィンドウ計算（target_date に対する JST 時刻 → UTC 変換）を提供。ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計。

- ツール
  - Paper Trading 向け検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - CLI オプション --from/--to/--db を提供。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出して人間向けレポートを標準出力へ出力。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数または --db により上書き可能。
    - 判定閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、Pass/Fail 判定を行う。

### Changed
- run_monitoring/run_execution の実行フロー設計上の決定事項:
  - 監視（monitoring）は常に本番 sqlite_path を参照（KABUSYS_ENV に依存しない）。一方、実行エンジンは is_paper 判定により paper_sqlite_path を用いて本番 DB と完全に分離する。
  - run_monitoring は例外発生時にループを止めず次のポーリングへ遷移（例外をログ出力して sleep）。

### Fixed
- env パーサーのクォート／エスケープ処理を強化し、.env 内の複雑な値取り扱い（バックスラッシュ・引用符を含む値や inline comment）に対応。

### Notes / Potential pitfalls
- 環境変数の必須チェック:
  - Settings の一部プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は _require を使って必須化しているため、未設定だと ValueError が発生します。デプロイ時は .env または環境変数の整備が必要です。
- PAPER_FILL_MODE は限定された有効値しか受け付けない（instant/partial/never/reject）。不正値は起動時に例外になります。
- process_priority/set_cpu_affinity は OS 権限やプラットフォーム依存で失敗することがあるため、失敗時は警告を出して処理を継続します。
- DuckDB / SQLite の利用:
  - DuckDB 接続は prices_daily / raw_financials 等のテーブルを前提とします。スキーマ・データの整備が必要です。
  - Paper Trading 検証ツールは対象テーブル（system_status, trade_logs, risk_logs 等）が存在しない場合に例外を捕捉して N/A を返すよう設計されています。

### Security
- OpenAI API キーは引数（api_key）または環境変数 OPENAI_API_KEY から取得。未指定の場合は ValueError を投げ、安全性を保っています。

---

今後の予定:
- 単体テストと統合テスト、CI ワークフローの追加（特に .env パーサーと AI バッチ処理のスタブ化）。
- 銘柄別 lot_size のマスタ化対応や、price フォールバック（前日終値など）の実装検討（position_sizing の TODO）。
- News NLP の部分失敗時の永続リトライ戦略と監視メトリクス連携強化。
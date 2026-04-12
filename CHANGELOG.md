# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-12

### 追加
- 初期リリース — KabuSys: 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン 0.1.0 を設定。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
      - .env ファイルの堅牢なパーサ（export プレフィックス、引用符、インラインコメント処理をサポート）。
      - Settings クラスを追加し、各種設定値（DB パス、PID/KILL フラグ、しきい値、環境モード等）をプロパティ経由で取得。入力値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
  - 実行／監視スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動エントリポイント。
      - KABUSYS_ENV=paper_trading 時に paper_trading DB を使用（本番 DB と分離）し、MockBrokerClient 利用を想定。
      - 起動時にプロセス優先度を高に設定。
      - Execution 用の主要コンポーネント組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
      - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動エントリポイント（デフォルト 60 秒）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルトへフォールバック）。
      - 監視 DB 初期化（init_monitoring_db）と duckdb 接続を確立。監視処理は本番 sqlite_path を使用（環境に依存しない）。
      - 起動時にプロセス優先度を高に設定。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプト（コマンドライン実行可能）。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計して PASS/FAIL 判定を出力。
      - 日付フィルタ、DB 存在チェック、SQL の OperationalError を扱うフォールバック処理を実装。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates, calc_equal_weights, calc_score_weights を追加（スコアに基づくソート・フォールバック挙動を含む）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes を追加（risk_based / equal / score の allocation、lot_size の丸め、aggregate cap のスケーリング、cost_buffer を考慮）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap（既存ポジションのセクター暴露による候補除外）と calc_regime_multiplier（市場レジームに応じた乗数）を追加。
    - パッケージエクスポートを src/kabusys/portfolio/__init__.py にて公開。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value を追加（DuckDB 上で prices_daily / raw_financials を参照、移動平均・ATR 等を計算）。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns, calc_ic, rank, factor_summary を追加（将来リターン、IC 計算、統計サマリー）。
    - src/kabusys/research/__init__.py で主要 API をエクスポート（zscore_normalize を data.stats から導入）。
  - AI ニュース NLP（OpenAI 連携）
    - src/kabusys/ai/news_nlp.py
      - raw_news を銘柄ごとに集約して OpenAI API（gpt-4o-mini）でセンチメントスコアを算出・ai_scores テーブルへ書き込み。
      - API バッチ処理（最大バッチサイズ 20）、トークン肥大対策（記事数・文字数制限）、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳格検証、スコアクリップを実装。
      - calc_news_window により JST ベースの時間ウィンドウを UTC に変換して照合。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - set_process_priority（Windows / POSIX の差分吸収、権限不足時に警告）と set_cpu_affinity（指定コア数への固定）を追加。
    - src/kabusys/utils/__init__.py を追加（モジュール初期化用）。

### 変更
- なし（初回リリースのため特記する過去からの変更はありません）。

### 修正 / 強化
- 設定読み込みの堅牢化
  - .env パーサで引用符内のエスケープや export プレフィックス、インラインコメントの取り扱いを改善し、OS 環境変数を保護する protected オプションを導入（自動ロード時の上書き制御）。
- run_monitoring のポーリング間隔取得
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出し、デフォルト値（60 秒）にフォールバックするようにした（time.sleep への不正入力を防止）。
- プロセス優先度設定の堅牢化
  - 未対応 OS の場合は設定をスキップして警告ログ。psutil による権限エラーや未実装例外を捕捉して警告を出すようにした。
- ポートフォリオ・ポジション計算の安全弁
  - position_sizing.calc_position_sizes で価格欠損時のスキップ、lot_size による丸め、aggregate cap 超過時のスケーリングと端数配分ロジックを実装し、投下額超過を回避。
- research モジュールの安定性
  - DuckDB クエリでウィンドウ関数を利用し、データ不足時（ウィンドウサイズ未満）は None を返すなど欠損扱いを明示的に処理。

### 既知の制約 / TODO
- position_sizing の price フォールバックは未実装（price が 0 の場合の保守的見積りについて注記あり）。
- news_nlp の処理は OpenAI API キーが必須。API 呼び出し失敗時はスキップする設計だが、部分失敗時の運用ポリシー（再試行やアラート）は今後整備予定。
- 将来的に個別銘柄の lot_size を stocks マスタで管理する拡張を想定（現在は全銘柄共通の lot_size）。

---

今後のリリースではテストカバレッジの向上、CI/CD の整備、外部依存ライブラリのバージョン固定・監視、より詳細な運用ドキュメント（デプロイ手順・監視アラート設計）を予定しています。
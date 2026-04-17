# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。

全般的な注意
- このドキュメントは、リポジトリ内のソースコードから推測して作成しています。実際のリリース履歴やタグ付けと異なる可能性があります。

## [0.1.0] - 初期リリース (推定)
リリース日: 2026-04-17 (ソース参照日)

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。
- 設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml）。
  - .env の柔軟なパース実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD の導入。
  - Settings クラスを追加し、環境変数から各種設定を取得するプロパティを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / 制御フラグ 等）。
  - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションと便利プロパティ（is_live, is_paper, is_dev）。
- 実行エントリポイント
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine の起動フローを実装（BrokerClientFactory によるブローカ抽象化、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て）。
    - paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル(data/execution.pid) の取り扱い。
    - RiskManager のデフォルト構成値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリング方式の監視ループ実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する挙動。
    - 停止フラグ (data/stop_requested.flag) によるループ終了判定。
- 監視 DB 初期化フック (monitoring_db 初期化呼び出しが run 系で行われる)
- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を追加（Windows と POSIX を吸収、"high"|"normal"|"low" をサポート）。
  - set_cpu_affinity(cpu_count) を追加（指定コア数に固定）。
  - 権限不足や未対応 OS に対する安全なフォールバック（警告ログ）。
- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限とレジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
  - 株数決定・リスク制限・単元丸め: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
  - モジュールエクスポートを整備（src/kabusys/portfolio/__init__.py）。
  - コメントや TODO により将来の拡張方針（lot_sizeの銘柄別対応等）を明示。
- 研究・リサーチモジュール (src/kabusys/research/*)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）。
    - モメンタム（1/3/6 カ月リターン、MA200乖離）、ATR、出来高・出来高比率、PER/ROE等を DuckDB を用いて計算。
    - データ不足時は None を返す等の堅牢性を確保。
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank（src/kabusys/research/feature_exploration.py）。
    - 複数ホライズンの将来リターンを一度のクエリで取得。
    - スピアマン IC（ランク相関）計算、統計サマリの実装（外部ライブラリ依存なし）。
  - 研究用 API をエクスポートする __init__ を追加。
- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading の検証レポート生成 CLI を追加。
  - 報告項目: 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等。
  - 判定基準（閾値）をコード内で定義（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）。
  - 日付フィルタ (--from/--to)、DB 指定 (--db) をサポート。DB が存在しない場合にわかりやすいエラー出力。
- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコアを計算・ai_scores へ保存する設計を実装。
  - バッチ処理 (最大 _BATCH_SIZE=20)、トークン肥大防止 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)、スコアクリップ (_SCORE_CLIP=±1.0)、再試行ロジック（429/ネットワーク/5xx に対する指数バックオフ）等を実装。
  - API キー解決ロジック（引数優先、環境変数 OPENAI_API_KEY 参照）、未設定時は ValueError を送出する仕様。
  - ニュースウィンドウ計算ユーティリティ calc_news_window を実装（JST ベース → UTC に変換）。
  - 出力フォーマットに対する厳密な JSON 検証方針や部分更新（DELETE→INSERT）によるデータ保護方針がコメントとして記載。
  - 注意: ファイル末尾が途中で切れているため、実装は途中（途中でトランケーション）と推定。

### 変更 (Changed)
- 起動スクリプトの挙動
  - run_monitoring.py と run_execution.py の起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority("high") を呼び出し）。
- DB 初期化
  - run_execution/run_monitoring が起動時に init_monitoring_db を呼び出し、監視テーブルの存在を冪等に保証するように（既存の DB に対して安全）。
- 環境変数ロードの優先順位
  - OS 環境 > .env.local > .env の順で読み込まれるよう明示（既存 OS 環境は保護される）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、コメント処理などに対応し、.env パーサーの誤解析を軽減。
- ポートフォリオ重み計算のフォールバック
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバック（警告ログ）。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_monitoring は「監視用 DB を本番用 sqlite_path で常に使用する」挙動になっているため、開発・テスト環境で実行する場合は sqlite_path の指定に注意してください（意図的な設計と思われる）。
- ai/news_nlp.py はファイル末尾で切れており（ソースが途中で終了）、完全実装済みかは不明です。OPENAI API を使うフローは概ね設計されているが、実行環境での動作検証が必要です。
- process_priority の設定は権限や OS に依存するため、実行ユーザーにより設定に失敗する場合があり、その際は警告ログが出力されフォールバックします。
- position_sizing や apply_sector_cap では price の欠損 (0.0) があるとエクスポージャー/サイズ計算に影響が出る旨の TODO が残っており、将来的な価格フォールバック実装が示唆されています。
- DuckDB を用いる研究系・AI系の関数群は、対応するテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）が存在することを前提としています。テーブルが存在しない場合は OperationalError をキャッチして N/A を返す実装（tools の報告処理等）もありますが、適切な初期データ投入が必要です。

### セキュリティ (Security)
- OpenAI API キーは環境変数 OPENAI_API_KEY により供給する想定。コードはキー未設定時にエラーを返す作りになっている（安全措置）。

---

今後のリリースでは、ai/news_nlp の完成、より詳細なテストケース、logging レベルやログ出力先の柔軟化、lot_size の銘柄別対応などが予想されます。必要であれば、ファイル単位でより詳細な変更点（関数ごとの説明や使用注意）を追加した CHANGELOG を作成します。
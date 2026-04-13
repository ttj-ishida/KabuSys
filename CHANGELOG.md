# Changelog

すべての非互換な変更はメジャーバージョンで行います。  
このファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]

- 開発中 / 予定
  - ai/news_nlp モジュールのエラーハンドリング周りや部分的失敗時の部分コミット保護処理の追加・堅牢化。
  - 実運用での監視・実行周りの運用ドキュメント（起動オプション・環境変数一覧）の整備。
  - 単体テストと CI ワークフローの整備（特に DuckDB / OpenAI 依存部のモック化）。

---

## [0.1.0] - 2026-04-13

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」 の基礎機能を含みます。主要な追加点は以下の通りです。

### 追加 (Added)
- アプリケーション設定管理
  - src/kabusys/config.py
    - プロジェクトルート（.git / pyproject.toml）を基準に .env 自動読み込み機能を実装（.env, .env.local の優先順位・上書き保護対応）。
    - 環境変数のパース実装（クォート・エスケープ・インラインコメント対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / PID/KILL フラグパス /閾値 等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証と専用プロパティ（is_live / is_paper / is_dev）を実装。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など Paper Trading 固有設定をサポート。

- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。環境に応じて paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッション実行。
    - 起動時にプロセス優先度を上げる処理を組み込み。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。

- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化の呼び出しを各起動スクリプト（冪等に保証）に追加。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows / POSIX 対応）。
    - カレントプロセスの CPU affinity を設定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構成
  - src/kabusys/portfolio/*
    - portfolio_builder: シグナル選定（score 降順、タイブレーク）、等金額・スコア重み計算を実装。
    - risk_adjustment: セクター集中上限適用（既存保有を考慮）および市場レジームに応じた乗数 calc_regime_multiplier を実装（未知レジームは警告してフォールバック）。
    - position_sizing: 発注株数算出（risk_based / equal / score）、単元株丸め、per-position と aggregate の上限、cost_buffer の考慮による保守的スケーリングを実装。
    - 上記をパッケージとしてエクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン・MA200 乖離）、Volatility（ATR20・流動性）、Value（PER・ROE）算出を DuckDB SQL で実装。
    - DuckDB 接続を受け取り prices_daily/raw_financials テーブルを参照する純粋関数群を提供。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを標準ライブラリのみで実装。
    - ties（同順位）時の平均ランク処理を実装。

  - research パッケージから主要関数をエクスポート（zscore_normalize は data.stats から）。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - CLI ツールを追加（--from / --to / --db オプション）。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（P95）を集計し PASS/FAIL 判定を出力。
    - DB が存在しない・テーブルがない場合のハンドリング（エラーメッセージやデフォルト値）を実装。
    - P95 計算、閾値（稼働率 99%、成功率 90% 等）を定義。

- ニュース NLP（AI）連携（初版）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30）を提供。
    - バッチサイズ、トークン肥大化対策（記事数/文字数上限）、API リトライ（429/ネットワーク/5xx のエクスポネンシャルバックオフ）やレスポンスバリデーション、スコアの ±1.0 クリップを考慮。
    - OpenAI API キーが未設定の場合は ValueError を送出。

### 変更 (Changed)
- 起動時のプロセス優先度を各起動スクリプトで明示的に "high" に設定するようにした（run_execution, run_monitoring）。
- run_execution:
  - paper_trading 環境時に専用の paper_sqlite_path を使用して DB を分離（data/paper_trading.db をデフォルト）。
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - RiskManager のデフォルトコンフィグ値をコード内に明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() を利用。

- .env ローダーの挙動
  - OS 環境変数を保護する protected セットを導入し、.env.local の override を制御。
  - export KEY=val 形式やクォート・エスケープ・インラインコメントの扱いを改善。

- ポートフォリオ / ポジションサイズ計算
  - 単元（lot_size）での丸め、aggregate cap 超過時のスケーリング（端数分を fractional_remainder によって再配分）を実装して、より実運用寄りの配分ロジックを導入。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL 取得処理の堅牢化（0 以下や非整数はデフォルトにフォールバックして警告を出力）。
- process_priority / cpu_affinity 設定は権限不足や未実装属性時に例外を上げず警告でスキップするように修正。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分にフォールバックし、警告ログを出すようにした。
- calc_regime_multiplier: 未知のレジームで警告を出し 1.0（フォールバック）を返すようにした。
- papers verification report:
  - DB テーブルが存在しない場合に sqlite3.OperationalError をキャッチしてサマリを欠損対応するようにした。
  - P95 計算は空リスト時に None を返すように修正。

### その他 / 注意事項
- DuckDB を利用する関数群は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取る設計で、外部副作用を持たない純粋関数を基本としています（テスト容易性を意図）。
- ai/news_nlp モジュールはネットワーク・課金を伴う処理のため、API キー管理と呼び出し回数に注意してください。未設定時は明示的にエラーを返します。
- run_monitoring は監視用 DB に本番 sqlite_path を使う点に注意（KABUSYS_ENV に依存しない）。

---

もしこの CHANGELOG に追加したい詳細（リリース日を変更する、特定コミットや PR を参照する等）があれば教えてください。必要に応じて各項目に参照元ファイル・行番号や関連 Issue/PR 番号を付加します。
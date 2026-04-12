CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。  
コードベースの内容から推測して作成した初期リリースの要約です。

Unreleased
----------

（現在の開発中の変更はここに記載します）

[0.1.0] - 2026-04-12
-------------------

### Added
- 初回リリース: 基本機能群を実装しました（パッケージ: kabusys）。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 と設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - Settings クラスを実装し、アプリケーション設定を環境変数から取得する仕組みを提供。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の読み込み順序・上書き規則を実装（OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - 各種設定プロパティ: DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグ、閾値（CPU/MEM/DISK）、KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL、PAPER_FILL_MODE 等の検証を実装。

- 実行用スクリプト（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
  - ExecutionEngine 起動エントリ（run_execution）:
    - KABUSYS_ENV=papaer_trading の場合に paper_trading 用 SQLite を使用して本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせ、ExecutionEngine を起動。
    - duckdb 接続を受け取りデータ処理に利用。
  - SystemMonitor のポーリングループ起動スクリプト（run_monitoring）:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に関係なく本番 sqlite_path を使用する設計。
    - KeyboardInterrupt による正常終了処理、例外時のログ出力と次ポーリングへの継続を実装。

- 監視 DB 初期化ユーティリティ（src/kabusys/monitoring/monitoring_db.py を参照する呼び出し箇所）
  - run 系スクリプトから init_monitoring_db を呼ぶことで監視テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) により Windows / POSIX に対応したプロセス優先度設定を実装（high/normal/low）。
  - set_cpu_affinity(cpu_count) による CPU ピンニング機能（利用可能であれば）。
  - 権限や未対応環境では安全にスキップして警告ログを出すフェイルセーフ。

- ポートフォリオ構築関連（src/kabusys/portfolio/*）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で切り詰め。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重み付け（スコア全員0時のフォールバック警告あり）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックで新規候補を除外するロジック（"unknown" は除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear + フォールバック）。
  - position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。lot_size（単元）丸め、max_position_pct・max_utilization・cost_buffer を考慮する aggregate scale-down ロジックを実装。
    - スケーリング後の端数配分（lot 単位で残余キャッシュを割当てる安定化ロジック）や価格欠損時のスキップなどの防御的実装。

- 研究（Research）モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 上で SQL ウィンドウ関数を用いてファクターを計算（MA200, ATR20 等）。
    - データ不足（十分なウィンドウがない場合）は None を返す等の扱い。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）を効率良く1クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード数が少ない場合は None）。
    - factor_summary, rank: 基本統計量・ランク付けユーティリティを実装。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋処理群として設計（本番ブローカ/API にアクセスしない）。

- ニュース NLP / AI スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを生成して ai_scores テーブルに書き込む処理を実装。
  - バッチ処理（最大 20 銘柄/API 呼び出し）、記事/文字数上限、レスポンス JSON 検証、スコア ±1.0 クリップ、429/ネットワーク/5xx のリトライ（指数バックオフ）等の堅牢化。
  - スコア反映は部分更新（該当コード群に対する DELETE → INSERT）で部分失敗時のデータ保護を考慮。
  - calc_news_window により JST 時刻ウィンドウを UTC naive datetime で計算しルックアヘッドバイアスを抑止。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - ローカルの paper_trading SQLite DB を走査して検証レポートを標準出力に出力する CLI ツールを追加。
  - システム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数などを集計し、PASS/FAIL を閾値と比較して判定。
  - 日付フィルタ (--from / --to)、DB パス指定 (--db) をサポート。DB が存在しない場合のエラーメッセージ、DB テーブルがない場合の安全なフォールバックを実装。

### Security / Reliability
- 環境変数の検証とデフォルト値を明示的に実装（不正値時は ValueError またはログ警告／デフォルトフォールバック）。
- DB/接続のクローズを finally ブロックで保証。
- 外部 API（OpenAI）周りはリトライ・検証・最小単位の置換で失敗時のリスクを低減。

### Notes / Requirements
- DuckDB、psutil、openai 等の外部依存が存在（requirements に追記が必要）。
- 実行方法（例）:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Paper Trading は production DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV）。

### Breaking Changes
- 初回リリースのため該当なし。

免責事項
--------
- 本 CHANGELOG は提示されたソースコードの内容から推測して作成したものであり、実際のリリースノートと差異がある可能性があります。必要に応じて追記・修正してください。
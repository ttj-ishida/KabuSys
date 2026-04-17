CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。記載内容はソースコードから推測して作成しています。

Unreleased
----------

- Notes
  - news_nlp モジュールの実装が途中で切れている可能性があります（ファイル末尾が不完全）。本番運用前に完了・確認してください。

0.1.0 - YYYY-MM-DD
-----------------

Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 環境/設定管理
  - robust な .env パーサを実装（kabusys.config）。
    - .env/.env.local を自動ロード（OS 環境変数を保護）。
    - export 形式やクォート、インラインコメント等に対応するパースロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 設定値取得用の Settings クラスを追加（データベースパス、API トークン、監視閾値、環境種別判定等をプロパティで提供）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。

- 実行用エントリスクリプト
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - プロセス優先度を設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager にデフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による安全停止機構を実装。
    - 起動前に init_monitoring_db を呼び出し監視テーブルの存在を保証。

  - 監視ループ起動スクリプト run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、非正の値や不正入力はデフォルトにフォールバック）。
    - 監視（Monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db 等）を使用。
    - SystemMonitor を初期化して定期的に check_once() を実行、停止フラグでループ終了。例外発生時はロギングして次回ポーリングへ継続。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルが存在することを保証（冪等）。

- プロセス制御ユーティリティ
  - kabusys.utils.process_priority を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は安全にスキップして警告ロギング。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順 + tie-breaker による銘柄選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0.0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限。既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear, 未知は 1.0 フォールバックかつ警告）。
  - position_sizing.py
    - calc_position_sizes: 複数の配分方式に対応（risk_based / equal / score）。
      - risk_based: 許容リスク率と stop_loss から株数を算出。
      - equal/score: ウェイトに基づく割当、per-position と aggregate の上限を尊重。
      - lot_size（単元株）で丸め、cost_buffer を考慮した保守的見積もりを実施。
      - aggregate cap を超える場合はスケールダウン・端数処理（lot 単位で残余配分）を実装。
      - 価格欠損や不正価格はスキップしてログ出力。

- 研究 / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB 上の prices_daily から計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算（欠損制御を厳格に実施）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（最新財務レコードの参照ロジックを実装）。
    - 全関数は DuckDB 接続を受け取り SQL で効率的に処理。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを LEAD を使って取得（複数ホライズンを一度に処理）。
    - calc_ic / rank: ランク相関（Spearman）を実装。ties の平均ランク処理と丸め誤差対策を含む。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出（None 値除外）。
  - research/__init__.py で主要関数をエクスポート（zscore_normalize を含む）。

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py を追加（OpenAI を用いたニュースセンチメントスコアリング）。
    - target_date に対するニュース収集ウィンドウ計算（JST→UTC の変換）を実装。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、1 銘柄あたりの記事数・文字数上限でトリム。
    - OpenAI（gpt-4o-mini）を JSON モードでバッチ送信（最大バッチサイズ 20）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ実装（上限回数設定）。
    - レスポンス検証、スコアを ±1.0 にクリップ、書き込みは部分的に安全に置換（DuckDB への安全な更新戦略）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - （注）実装末尾が途中で切れているため、実行前に完全実装が必要。

- ツール
  - tools/paper_verification_report.py を追加。
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 閾値（PASS/FAIL 基準）を定義: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms。
    - 日付フィルタ（--from/--to）、--db オプション対応、DB 存在チェック、欠損テーブルに対するフォールバック処理を実装。

Changed
- 環境変数ロードの優先順位を明文化
  - OS 環境 > .env.local > .env の順でロードし、デフォルトの安全性を確保。

Fixed
- （初期リリース）.env パーサの解釈精度向上により、クォート・エスケープ・コメント処理に関する既知のパース問題を解消。

Known issues / Notes
- ai/news_nlp.py の末尾が切れている（ファイルの途中で終端している）。OpenAI へのリクエスト実行・結果書き込みの続き実装が必要。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張や price フォールバック）が残っている。将来的な改善点として計画することを推奨。

参考: 環境変数
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KABUSYS_ENV — 起動環境（development | paper_trading | live）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite パス（data/paper_trading.db）
- PAPER_FILL_MODE — paper trading の fill モード（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp が使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化フラグ（1 で無効化）

以上。ソースコードの差分や追加要望があれば、それに応じて CHANGELOG を更新します。
CHANGELOG
=========

すべての変更は Keep a Changelog の方針に沿って記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。Paper Trading 環境時は専用の MockBrokerClient と分離された SQLite DB（data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 両スクリプトとも起動直後にプロセス優先度を設定する処理を実装（utils.process_priority.set_process_priority を使用）。

- 環境設定関連
  - config.Settings を導入し、環境変数および .env / .env.local ファイルから設定を読み込む自動ロード機構を実装（プロジェクトルート探索は .git または pyproject.toml を基準）。
  - .env パーサーでクォート付き値、エスケープ、インラインコメント（クォート無効時の '#' 処理）、export プレフィックスに対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。OS 環境変数を保護するための上書き制御を実装。
  - Settings に各種プロパティを実装（J-Quants / Kabu API / LINE / DB パス / PID/KILL フラグ / リソースしきい値 / 環境判定など）。PAPER_FILL_MODE の入力検証と PAPER_TRADING_SQLITE_PATH のサポートを追加。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_execution/run_monitoring で行い、監視用テーブルの存在チェックを保証（冪等）。

- Portfolio コンポーネント（純粋関数群）
  - portfolio.portfolio_builder: BUY シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）と、等金額配分 / スコア加重配分を実装。スコア全てが 0 の場合は等金額にフォールバックして警告ログを出力。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有のセクター別時価を計算して新規候補を除外）。レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に基づいて発注株数を計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash によるスケールダウン）と残差の lot 単位での再配分ロジックを実装。コストバッファ（手数料・スリッページ見積り）対応。価格欠損時のスキップやデバッグログを追加。

- 研究（research）モジュール
  - research.factor_research:
    - モメンタム（1M/3M/6M、MA200 乖離）計算。
    - ボラティリティ（ATR20、ATR 比率、20 日平均売買代金、出来高比）計算。
    - バリュー（PER、ROE）計算（raw_financials の最新レコードを利用）。
    - DuckDB を使用した SQL ベースの実装で、データ不足時は None を返す設計。
  - research.feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - Spearman ランク相関に基づく IC（calc_ic）およびランク計算ユーティリティ。
    - factor_summary による基本統計量算出（count/mean/std/min/max/median）。
  - research パッケージから主要関数をエクスポート。

- AI ニュース NLP（news_nlp）
  - raw_news を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込む処理を実装。
  - 処理の設計方針として、ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を参照しない）、バッチ送信（最大 20 銘柄/回）、トークン肥大化対策（記事数最大・文字数トリム）、429/ネットワーク/5xx のリトライ（指数バックオフ）実装、レスポンスの JSON バリデーション、スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するために対象コードを絞って置換操作する設計を採用。
  - calc_news_window により JST ベースのニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC naive datetime で計算。

- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して検証レポートを出力する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、閾値（稼働率 99%、成功率 90% 等）で PASS/FAIL 判定を出力。P95 計算、日付フィルタ、DB 存在チェック、SQL の例外ハンドリング（テーブル未存在時のフォールバック）を実装。

- ユーティリティ
  - utils.process_priority:
    - プラットフォーム（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定する API を追加。サポートされない OS では警告を出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。AccessDenied 等の例外は警告して安全にスキップ。

Changed
- DB 接続の扱い
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する方針で実装。実行エンジン（run_execution）は Paper Trading 環境時に paper_sqlite_path を使用して本番 DB と分離するよう変更。

- エラーハンドリング強化
  - ポーリングループ内で monitor.check_once() が例外を投げてもループを継続し、スタックトレースをログに出力して次のポーリングに移るようにした（run_monitoring）。
  - 各種外部アクセス（OpenAI、psutil 設定等）で権限エラーや未実装エラーを捕捉してフォールバックする実装を追加。

Fixed
- 環境変数パースの堅牢化
  - _parse_env_line でクォートとエスケープ、コメント判定の細かいケースに対応。これにより .env の複雑な値が正しく扱われるようになった。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL の値が 0 以下または数値以外の場合にデフォルト値へフォールバックする検証を追加。time.sleep に渡す不正値による例外を防止。

- position_sizing のスケーリング精度向上
  - aggregate cap スケールダウン時に lot_size 単位での端数処理と残余キャッシュを用いた再配分ロジックを導入し、投資金額の利用効率を改善。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決し、未設定時は明示的な ValueError を発生させるようにして誤設定を検出しやすくした。

Notes / Misc
- パッケージバージョンは kabusys.__version__ = "0.1.0"。
- DuckDB / SQLite を併用する設計（分析用に DuckDB、軽量なログ・監視に SQLite）を採用。
- 各モジュールは可能な限り副作用を持たない純粋関数として設計され、テストしやすさを考慮。

今後の予定
- stocks マスタを用いた銘柄別 lot_size 対応（position_sizing の拡張）。
- news_nlp の API 呼び出しエラーハンドリングのさらに詳細なメトリクス収集。
- paper_verification_report に HTML/CSV 出力オプションの追加。
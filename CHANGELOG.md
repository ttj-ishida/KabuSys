CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
リリース日付はコードベースの作成日として 2026-04-16 を使用しています（推測）。

Unreleased
----------
（現在なし）

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初期公開
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - パブリック API を __all__ でエクスポート（data, strategy, execution, monitoring 等のサブパッケージを意図）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - プロセス優先度を高に設定し、stop フラグファイルで終了を制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager/RiskManager/Reconciler を組み立ててスレッド実行。
    - 停止フラグと pid ファイルを用いた起動/停止制御。

- 設定 / 環境変数管理
  - config.py を導入し、.env/.env.local の自動ロードを提供（OS 環境変数をデフォルトで保護）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - .env のパースで export 形式、クォート、行内コメントなどに対応。
    - プロジェクトルートの検出ロジックを追加（.git または pyproject.toml を基準）。
  - Settings クラスを導入し、各種設定値（API トークン、DB パス、PID パス、監視閾値、環境種別等）にアクセスできる統一インターフェースを提供。
    - env（KABUSYS_ENV）、log_level の検証（有効値チェック）。
    - PAPER_FILL_MODE（paper trading の fill 動作）に対する検証（有効値: instant|partial|never|reject）。
    - paper_trading 用 sqlite パス（PAPER_TRADING_SQLITE_PATH）等を定義。

- モニタリング / 検証ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを生成する CLI ツール。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - P95 計算、各種 SQL クエリとフォーマッタを実装。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順での候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存ポジションのセクター比率が上限を超える場合に当該セクターの新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。
      - risk_based: 許容リスク率・損切り率から基準株数を計算。
      - equal/score: 重みから配分、per-position 上限・aggregate cap（利用可能現金）を考慮。
      - 単元株（lot_size）で丸め、コストバッファを考慮したスケールダウンと端数配分アルゴリズムを実装。

- リサーチ / ファクター計算
  - research/factor_research.py を追加。DuckDB 上の prices_daily / raw_financials を用いたファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務データを取得し PER, ROE を計算。
  - research/feature_exploration.py を追加。
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。
    - calc_ic: スピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank / factor_summary: ランク付けと統計サマリー機能。
  - research/__init__.py で zscore_normalize（data.stats から）と主要関数をエクスポート。

- AI / ニュース NLP スコアリング
  - ai/news_nlp.py を追加。
    - raw_news + news_symbols からニュースを銘柄別に集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を生成して ai_scores に格納するフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）、記事トリム（記事数 / 文字数上限）、バッチ送信（最大 20 銘柄/コール）、JSON 出力期待、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 でのクリップなどを設計に明記。
    - API キー未設定時は ValueError を送出。
    - （注）ファイル末尾が途中で切れているように見えるため、実装は一部未完の可能性あり（コードからの推測）。

- ユーティリティ
  - utils/process_priority.py を追加。
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供。
    - 権限不足や未対応 OS に対する安全なフォールバックと警告ログを出力。

Changed
- DB 初期化の冪等性確保
  - run_execution.py / run_monitoring.py で init_monitoring_db(sqlite_conn) を呼び出し、監視テーブルの存在を保証（何度呼んでも安全な初期化）。

Fixed
- 環境変数パーサの堅牢化
  - _parse_env_line が export プレフィックス、引用符内のエスケープ、行内コメントの取り扱いを適切に処理するよう改善。

- ポートフォリオ計算の端数処理
  - calc_position_sizes の aggregate cap 適用時に lot_size 単位での端数処理と残余キャッシュの再配分を実装し、より安定した丸め挙動を実現。

Security
- 環境変数の保護
  - .env/.env.local の自動読み込みで既存の OS 環境変数はデフォルトで上書きされない（protected 機構）。自動ロードを明示的に無効化するフラグを用意。

Notes / その他
- デフォルトのファイルパスはコード中に明記（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid 等）。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨が設計コメントに明記されているため、監視アクションは実運用 DB を参照する点に注意が必要。
- news_nlp.py は OpenAI を用いた外部 API 連携を行うため、運用時には OPENAI_API_KEY のセットとコスト管理が必要。
- 一部関数（特に ai/news_nlp.py の後半）はソースが途中で切れているように見えるため、完全実装やテストは要確認。

参考
- 本 CHANGELOG は提供されたソースコードの内容を基に推測して作成しています。実際の変更履歴（コミット単位）や公開リリースのノートがある場合は、そちらを優先してください。
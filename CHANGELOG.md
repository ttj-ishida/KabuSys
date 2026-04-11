# Changelog

すべての変更は Keep a Changelog の仕様に準拠し、重要な変更点はセマンティックバージョニングに従います。

- リリース日付は本リポジトリ内の __version__ = "0.1.0" を基準に付与しています。

## [Unreleased]

（現時点で未リリースの変更なし）

## [0.1.0] - 2026-04-11

初期公開リリース。自動売買システム KabuSys のコア機能群を提供します。主要な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 公開 API を kabusys.portfolio / kabusys.research などでエクスポート。

- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）へ記録し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定する初期処理を追加。
    - 依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てとセッション実行を行う。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等性）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能を追加（OS 環境変数 > .env.local > .env の優先順位）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 等）の検証ロジックを提供。
    - PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を追加。
    - pid_file_path / kill_flag_path 等の監視関連設定プロパティを追加。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX の差を吸収）。
    - set_cpu_affinity(cpu_count) を実装（指定数に CPU affinity を固定）。
    - psutil の権限不足や未対応プラットフォーム時に安全にスキップし警告を出力。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有比率に基づき新規候補を除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（'bull'/'neutral'/'bear'）に応じた投下資金乗数を計算。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づいた発注株数算出。単元株丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した安全なスケーリングおよび端数配分ロジックを実装。

  - portfolio/__init__.py で上記関数をエクスポート。

- リサーチ（ファクター計算・特徴量解析）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時の扱いを明記。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御等を実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得は ROW_NUMBER ベース）。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）を LEAD を用いて一度に取得。horizons の検証を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足時は None。
    - rank, factor_summary: ランク付け（同順位は平均ランク）・基本統計量生成ユーティリティを追加。
    - pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。

  - research/__init__.py で主要関数（zscore_normalize を含む）をエクスポート。

- AI（LLM）関連機能
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI の gpt-4o-mini を用いて銘柄ごとのセンチメント（ai_score）を生成・ai_scores テーブルへ安全に書き込む処理を実装。
    - タイムウィンドウの定義（JST 基準: 前日 15:00 〜 当日 08:30）と calc_news_window ユーティリティを提供。
    - バッチ処理 (_BATCH_SIZE=20)、1 銘柄あたりの文字数/記事数上限、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップを実装。
    - API リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ実装。失敗時は部分スコアだけをロールフォワードし、部分失敗で既存スコアを消さない（DELETE → INSERT をコード単位で実行）。
    - OpenAI 呼び出しを _call_openai_api に抽象化し、テストで差し替えやすく設計。

  - ai/regime_detector.py
    - ETF 1321 の 200 日 MA 乖離（ma200_ratio）とマクロニュース LLM センチメントを合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定する機能を実装。
    - マクロキーワードセットによる raw_news のフィルタリング、LLM 呼び出し（gpt-4o-mini）、合成スコア計算（MA 重み 70%・マクロ重み 30%・スケーリング）、閾値ベースでレジームを決定。
    - 書き込みは冪等操作（BEGIN / DELETE / INSERT / COMMIT）で実行。LLM 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ実装。

- データベース初期化
  - monitoring_db.init_monitoring_db を各実行スクリプトで呼び出し、監視用テーブルが存在することを保証（冪等）。

### Changed
- （初回リリースのため過去からの変更点なし）

### Fixed
- （初回リリースのため過去からの修正点なし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から取得。未設定時は明示的なエラーを返すように実装。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト等での誤注入防止）。

### Notes / Operational details
- run_monitoring は監視用に常時稼働するポーリングループを提供します。MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を設定可能。不正な値（整数変換失敗、0 以下）はデフォルト 60 秒にフォールバックして警告を出力します。
- run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番監視 DB（SQLITE_PATH）とは分離されます。監視テーブルは常に init_monitoring_db によって存在が保証されます。
- process_priority / cpu_affinity の設定では権限不足や未対応プラットフォームで安全にスキップされ、警告ログを出します。
- DuckDB に対する executemany は空リストを受け付けないバージョン（例: DuckDB 0.10）への互換性を考慮し、空チェックを行ったうえで実行する実装になっています。
- LLM 呼び出しは冗長性（リトライ・バックオフ・部分書き込み保護）を考慮した設計です。ただし、API の利用にはレート制限やコストが発生するため運用時は注意してください。

## 既知の制約・今後の改善予定（抜粋）
- position_sizing の lot_size は現状全銘柄共通の固定値（デフォルト 100）。将来的には銘柄別 lot_map への対応を検討。
- apply_sector_cap の価格欠損時（price が 0.0）の扱いに注釈あり。前日終値や取得原価をフォールバックする実装を検討中。
- news_nlp / regime_detector の LLM 呼び出しは gpt-4o-mini を想定。モデル変更やプロンプト改善、応答形式の更なる堅牢化（スキーマ検証等）を今後検討。

----

参照:
- コード中のドキュメント（module docstrings）および Settings のプロパティ説明を元にまとめました。
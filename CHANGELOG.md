CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠で記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース。KabuSys のコア機能群を追加しました。
  - パッケージ初期化とバージョン
    - __init__.py にてパッケージ名とバージョンを定義（バージョン: 0.1.0）。

  - 設定管理（src/kabusys/config.py）
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
    - 高度な .env パーサ実装（export 形式対応、クォート内エスケープ、インラインコメント処理）。
    - 環境変数取得ユーティリティとバリデーション（必須変数チェック、KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証）。
    - DB パス、PID/KILL フラグ、監視しきい値等の設定プロパティを提供。

  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - 起動時にプロセス優先度を "high" に設定。
      - Paper trading（KABUSYS_ENV=paper_trading）の場合は paper_trading 用 SQLite を利用して本番 DB と分離。
      - duckdb 接続を使用。
      - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。
    - run_monitoring.py: SystemMonitor（監視ループ）起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境に関係なく本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定し、SystemMonitor.check_once() を定期実行。

  - ユーティリティ（src/kabusys/utils/process_priority.py）
    - プロセス優先度設定ユーティリティを追加。
      - Windows（psutil の PRIORITY_CLASS ）および POSIX（nice 値）を吸収。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
      - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

  - ポートフォリオ構築（src/kabusys/portfolio/）
    - portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）。
      - スコアが全て 0 の場合は等金額配分へフォールバック。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
      - unknown セクターはセクター上限適用対象外。
      - レジーム乗数は bull/neutral/bear をデフォルトマップで提供。未知レジームは警告の上で 1.0 にフォールバック。
    - position_sizing: 発注株数決定ロジック（calc_position_sizes）。
      - allocation_method に応じた計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料・スリッページ見積）を考慮。
      - スケーリング時に端数分配ロジックで lot_size 単位の再配分を実施。

  - 研究（research）モジュール（src/kabusys/research/）
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実装）。
      - mom_1m/3m/6m、ma200_dev、atr_20 / atr_pct、avg_turnover、volume_ratio、per/roe などを計算。
      - データ不足時（ウィンドウ不足）は None を返す設計。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティ。
      - calc_forward_returns は複数ホライズンに対応（デフォルト [1,5,21]）、入力検証あり。
      - calc_ic はスピアマン ランク相関を実装（ties の平均ランク処理、最小サンプル数チェック）。
    - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポートし、主要関数を __all__ で公開。

  - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ格納する機能を追加。
    - 処理の特徴:
      - 時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に計算する calc_news_window。
      - 1 銘柄あたりの記事件数・文字数上限（トークン肥大化対策）。
      - バッチサイズ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）。
      - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
      - DuckDB ベースの読み書きを想定（raw_news / news_symbols / ai_scores）。
    - 実装は API 呼び出し・バッチ処理・書き込みまでの設計を含む（注: 一部ファイル末尾が切れているため実装が途中である可能性あり）。

  - ツール（src/kabusys/tools）
    - paper_verification_report.py:
      - Paper Trading の検証レポート生成ツールを追加。
      - 日付フィルタ（--from / --to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）。
      - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して人間向けレポートを標準出力に出力。
      - Pass/Fail 基準としきい値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200 ms）。
      - P95 計算、欠損テーブルに対する寛容な例外処理を実装。

  - DB 初期化ユーティリティ
    - monitoring.monitoring_db.init_monitoring_db を各ランナーで呼び、監視テーブルの存在を冗長に保証（冪等に初期化）。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数や外部依存での失敗時に安全にフォールバックする挙動を多くの箇所で実装（例: MONITOR_POLL_INTERVAL の不正値、process_priority の権限不足、DuckDB/SQLite テーブル欠損時のツール挙動など）。

Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数から取得する設計。README/.env.example に従って管理することを想定。

Notes / Known issues
- src/kabusys/ai/news_nlp.py のファイル末尾が切れている（提供されたコードが途中で終端している）。実行環境での完全動作確認時は該当ファイルの続き（書き込み部分やエラーハンドリングの最終処理）を確認してください。
- position_sizing の price 欠損時の挙動については TODO コメントがあり、将来的にフォールバック価格の導入を検討する旨が記載されています。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やパッケージ化環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により手動での制御が必要になる場合があります。

Acknowledgements
- DuckDB を利用したオンメモリ SQL 処理や psutil を用いたプロセス制御など、複数の外部ライブラリを活用した実装が含まれます。各実行環境で必要な依存関係のインストールを行ってください。
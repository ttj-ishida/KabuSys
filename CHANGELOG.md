CHANGELOG
=========

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマット:
- 重要な変更のみを記載しています（内部リファクタやコメントのみの変更は省略）。
- リリース日はリポジトリのスナップショット日（推定）を使用しています。

Unreleased
----------

（現時点の作業中の変更はここに記載してください）

[0.1.0] - 2026-04-12
-------------------

初期リリース（コードベースから推測）

### 追加 (Added)
- パッケージ基本情報
  - パッケージバージョンを __version__ = "0.1.0" として導入。

- 設定・環境変数管理
  - Settings クラスを実装し、各種環境変数をプロパティとして取得可能に。
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサーで以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ
    - インラインコメントの扱い（クォート有無で動作を分岐）
  - 設定値の検証を導入:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/...）
    - PAPER_FILL_MODE（instant/partial/never/reject）
  - データベース関連設定:
    - duckdb_path、sqlite_path、paper_sqlite_path、pid_file_path、kill_flag_path 等のプロパティを提供。
  - 監視・閾値設定:
    - cpu/memory/disk の閾値プロパティ（デフォルト値あり）。

- 実行スクリプト / デーモン化用ユーティリティ
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する点を明示。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアントの抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動。
    - RiskManager 用のデフォルト RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等処理）。

- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成スクリプトを追加。
    - CLI (--from, --to, --db) を提供。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
    - 稼働率、注文成功率（fill/send）、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL 判定を出力。
    - 判定用の閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）。
    - SQLite テーブルが存在しない場合のフォールバック（OperationalError をキャッチして N/A 扱い）。

- ポートフォリオ構築（Portfolio）
  - portfolio モジュール群を追加（純粋関数群、DB 非依存、メモリ計算のみ）:
    - portfolio_builder: select_candidates（スコア降順で上位選抜）、calc_equal_weights、calc_score_weights（スコア合計が0のとき等配にフォールバック）を実装。
    - risk_adjustment: apply_sector_cap（既存保有と当日売却予定を考慮してセクター上限を適用）、calc_regime_multiplier（bull/neutral/bear に対する投下乗数）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 考慮、手数料・スリッページ保守見積りを反映）。
  - 将来的な拡張点（TODO）をコード内に明記（銘柄別 lot_size、価格フォールバックなど）。

- 研究（Research）
  - research パッケージを追加:
    - factor_research:
      - calc_momentum（1M/3M/6M リターン、MA200 乖離など）
      - calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）
      - calc_value（PER / ROE の計算、raw_financials と prices_daily の結合）
      - DuckDB を用いた SQL ベースの実装。窓関数 / 過去データ不足時の None 処理を実装。
    - feature_exploration:
      - calc_forward_returns（複数ホライズンに対応、horizons の検証）
      - calc_ic（スピアマン順位相関（IC）計算。3 銘柄未満は None）
      - rank（同順位は平均ランクで扱う）
      - factor_summary（count/mean/std/min/max/median を計算）
    - research.__init__ で主要関数を公開（zscore_normalize は data.stats から再利用）。
  - DuckDB 接続を引数に取り、外部 API に依存しない設計。

- AI（ニュース NLP）
  - ai/news_nlp.py を追加:
    - raw_news と news_symbols を集約して銘柄ごとにテキストを作成し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを取得。
    - バッチサイズは 20 銘柄、最大記事数 / 文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ実装（上限 _MAX_RETRIES）。
    - レスポンス検証、スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するためコード絞り込みで DELETE/INSERT を実行する方針。
    - calc_news_window でニュース集約ウィンドウ（JST→UTC 変換）を定義（前日 15:00 JST ～ 当日 08:30 JST 相当）。
    - OpenAI API キー未設定時は明示的に ValueError を送出。

- ユーティリティ
  - utils/process_priority.py を追加:
    - set_process_priority(level)（Windows / POSIX を吸収して優先度設定。未対応 OS はスキップ）
    - set_cpu_affinity(cpu_count)（最初の N コアに固定。引数検証と例外ハンドリングあり）
    - psutil ベースで実装、権限不足や未実装 API 時は警告でスキップ。
  - run_* スクリプトで起動時に set_process_priority("high") を呼び出す設計。

- DB ドライバ
  - DuckDB（duckdb）を研究・AI・実行系で使用する構成を採用（duckdb_conn を各コンポーネントに注入）。

### 変更 (Changed)
- なし（初回公開のため、既存からの変更履歴は推測不可）。

### 修正 (Fixed)
- なし（初回公開のため、既存からの修正履歴は推測不可）。

### 注記 / 既知の設計上の注意点
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用するため、監視用途の DB 取り扱いに注意が必要。
- run_execution は paper_trading 環境で paper_sqlite_path を使用し本番 DB と分離する設計になっている。
- portfolio.position_sizing の aggregate スケーリングや端数処理は lot_size 単位で丸めるため、小口資金のケースでは意図しない切り捨てが発生する可能性あり。将来的に銘柄別 lot_size の導入を想定。
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊環境では自動ロードがスキップされる場合あり（KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能）。
- ai/news_nlp は OpenAI API を利用するため、API キー管理と利用料金に注意。API の部分障害に対してはフェイルセーフ（スキップ継続）を採用。

セキュリティ
------------
- 環境変数経由で API キーを扱う設計（OPENAI_API_KEY 等）。公開リポジトリに鍵を置かないこと。

今後の TODO（コード内でも言及あり）
- portfolio の銘柄別 lot_size サポート（stocks マスタに lot_size を持たせる等）
- position_sizing における価格フォールバック（前日終値や取得原価など）
- ai/news_nlp の部分失敗時のロールバック/再試行ポリシーの強化
- より詳細なモニタリング（duckdb 側のメトリクス取り込みなど）

脚注
----
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成したものです。実際のコミット履歴やリリースノートはソース管理履歴を参照してください。
# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※ 本ドキュメントは与えられたコードベースの内容から機能・挙動を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: kabusys パッケージの基本機能を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。

- 環境設定/ローディング（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml ベース）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサーは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントなどを考慮して安全にパース。
  - Settings クラスを提供し、各種設定値（API トークン、DB パス、PID／フラグパス、しきい値、環境種別など）をプロパティで取得。
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - デフォルト値（例: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db", PAPER_TRADING_SQLITE_PATH="data/paper_trading.db" 等）を定義。

- 実行・監視スクリプト
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し、本番DBと完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager の既定設定値を含む RiskConfig を定義（max_position_pct 等）。
    - エンジンは別スレッドで起動し、data/stop_requested.flag を監視して安全に停止可能。実行中 PID を data/execution.pid に保存する想定。
    - 監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動エントリポイント。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する設計（監視データは環境に依存せず一元管理）。
    - ループは data/stop_requested.flag を検出して終了。check_once() の例外はログ出力して次回ポーリングへ継続。

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) 実装（Windows と POSIX(Linux/Darwin/FreeBSD) を吸収）。
  - set_cpu_affinity(cpu_count) 実装（指定コア数でプロセスをピン留め、権限不足等は警告でスキップ）。
  - 権限不足や未対応 OS の場合は安全にフォールバックしてワーニングを出力。

- ポートフォリオ構築（src/kabusys/portfolio/*.py）
  - portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア配分 calc_score_weights を実装。スコア全ゼロ時は等金額配分にフォールバックして警告。
  - risk_adjustment: apply_sector_cap（セクター集中制限により候補を除外）、calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた投下資金乗数、未知レジームは警告して 1.0 フォールバック）。
  - position_sizing: calc_position_sizes 実装。allocation_method= "risk_based" / "equal" / "score" をサポートし、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）を考慮。cost_buffer による保守的コスト見積り／スケールダウン処理を実装。内部で複雑なスケーリングと端数分配ロジックを扱う。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research: DuckDB 接続を利用したファクター群を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジックを含む）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: Spearman ランク相関（IC）計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と各種統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize を含む想定）。

- ニュース NLP スコアリング基盤（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理フローを実装（スケルトン／主要ロジックを含む）。
  - 機能:
    - ニュース収集ウィンドウ計算（JST ベースで前日 15:00 〜 当日 08:30 を UTC に変換する calc_news_window）。
    - 記事集約、1銘柄あたり最大記事数・文字数トリム、バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフとリトライ。
    - レスポンス検証、スコア ±1.0 にクリップ、部分更新（対象コードのみ DELETE→INSERT）による安全な書き込みを想定。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - 注意: 提供コードは _fetch_articles 関連で途中までの実装が含まれ、ファイル末尾は途中で切れている（与えられたコード範囲では記事取得ロジックの細部が含まれていない）。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - CLI から paper_trading 用 SQLite DB を解析して検証レポートを生成。
  - オプション: --from, --to（日付フィルタ）、--db（DB パス）。
  - 指標:
    - システム稼働率（system_status テーブル）
    - 注文成功率 / 送信率（trade_logs テーブル）
    - リスク却下数（risk_logs）
    - レイテンシ（平均 / 最大 / P95）
  - PASS/FAIL 判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。データ不足やテーブル欠如に対しては N/A で扱いフェイルセーフに実装。
  - 実行例: python -m kabusys.tools.paper_verification_report

- 監視 DB 初期化ユーティリティ（src/kabusys/monitoring/monitoring_db.py を参照する呼び出し）
  - run_monitoring / run_execution から init_monitoring_db(sqlite_conn) を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーなどの秘匿情報は Settings 経由および環境変数で管理。`.env` の読み込み時に OS 環境変数のキーは上書きされない（protected 機構）。

### Notes / その他の設計上の注記
- run_monitoring は Monitoring 用に常に settings.sqlite_path（本番）を使用する設計になっているため、paper_trading 環境で監視データを分離したい場合は追加の設定変更が必要。
- position_sizing の価格欠損（price が 0.0 や未定義）の扱いに関する TODO コメントあり（将来的に前日終値や取得原価などのフォールバックを検討可能）。
- ai/news_nlp.py は堅牢なリトライ・バリデーション設計だが、与えられたスニペットでは記事取得部（_fetch_articles 等）が途中で終わっているため、完全動作にはその実装が必要。
- DuckDB を前提としたファクター計算は SQL ウェイトを多用しており、prices_daily / raw_financials 等のテーブル構造に依存する。実データ投入前にスキーマ整合性確認が必要。

---

（以降のリリースでは変更点をこのフォーマットで追記してください）
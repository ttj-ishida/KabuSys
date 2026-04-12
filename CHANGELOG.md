# CHANGELOG

すべての重要な変更は「Keep a Changelog」形式で記録します。  
フォーマット: https://keepachangelog.com/ja/

全般:
- このリポジトリはバージョン管理された初期リリースとして機能する一連のモジュールを含みます。  
- バージョンはパッケージ定義 (kabusys/__init__.py) により 0.1.0 として公開しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-12
初期リリース。以下の主要コンポーネントと機能を追加。

### Added
- パッケージ基盤
  - kabusys パッケージ本体を追加。バージョン __version__ = "0.1.0" を定義。
  - __all__ に主要サブパッケージを公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得する仕組みを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート (.git または pyproject.toml を探索) を基に .env と .env.local を自動読み込み。
    - OS 環境変数は保護され、.env.local は上書き可能（保護されたキーは上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env ファイルのパースは export 形式・クォート・エスケープ・インラインコメントに対応。
  - 多数のプロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定など）。
  - 環境変数のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。

- プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を追加。Windows と POSIX (Linux/Mac/FreeBSD) を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity 設定を提供。
  - 権限不足や未対応プラットフォーム時には警告を出して処理をスキップするフェイルセーフを実装。

- 実行エントリスクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine を起動する CLI スクリプトを追加。
  - 起動時にプロセス優先度を "high" に設定。
  - DB 接続: 本番/ペーパーを分離（KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
  - BrokerClientFactory を使ってブローカークライアントを生成（ペーパー時は MockBrokerClient を使用する想定）。
  - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
  - RiskConfig によるデフォルト制約（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）を導入。
  - duckdb を補助的に使用（duckdb_path）。

- 監視ループエントリスクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
  - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計（monitoring は常に本番 DB を参照する）。
  - 起動時にプロセス優先度を "high" に設定。
  - 例外発生時はログ出力して次ポーリングに継続するフェイルセーフを実装。

- 監視 DB 初期化 (monitoring_db 呼出し点)
  - run_execution, run_monitoring 両方で init_monitoring_db を呼び、監視用テーブルが存在することを冪等的に保証。

- Portfolio 構築ライブラリ (src/kabusys/portfolio/*.py)
  - portfolio_builder:
    - select_candidates: スコア降順（タイブレークに signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装。全スコアが0のとき等配分にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して特定セクターの新規候補を除外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をマップ、未知はフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算、単元株丸め、per-stock/max aggregate cap、スケールダウン処理、cost_buffer による保守的見積もり、残差配分ロジック等を実装。
  - いずれも純粋関数で DB 参照なし（メモリ内計算のみ）。将来改善点（lot_size 銘柄別対応、フォールバック価格など）を TODO として明示。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクター（1M/3M/6M リターン、MA200乖離、ATR20、20日平均売買代金、PER/ROE 等）を計算。
    - データ不足時の None ハンドリング、ウィンドウサイズやスキャン範囲の設計が明記。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（horizons デフォルト [1,5,21]）を計算。入力検証あり（horizons は 1..252）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足・同値・ties の扱いに対応。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリーの提供。
  - research パッケージは zscore_normalize を kabusys.data.stats から再公開。

- AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - OpenAI API（gpt-4o-mini）を用いたニュース記事のセンチメントスコアリング機能を追加。
  - 主な特徴:
    - ニュース収集ウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う)。
    - raw_news と news_symbols を集約し、銘柄単位に記事をトリム（最大記事数・文字数制限）。
    - 最大 20 銘柄/バッチで API 呼び出し（JSON Mode を期待）し、429/タイムアウト/5xx は指数バックオフでリトライ（上限あり）。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは対象コードごとに部分置換（DELETE → INSERT）して部分失敗時の他銘柄データ保護を実施。
    - API キー未設定時は ValueError を送出。api_key 引数で上書き可能（未指定なら環境変数 OPENAI_API_KEY を参照）。
    - フェイルセーフ: API 失敗時は処理をスキップして継続。
    - 実装注記として executemany の空パラメータ回避など DuckDB 固有の注意点を記載。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 向け検証レポート生成スクリプトを追加。
  - CLI から期間指定 (--from / --to) および DB パス (--db) が可能。環境変数 PAPER_TRADING_SQLITE_PATH と併用可。
  - 判定基準（稼働率・注文成功率・送信率・P95 レイテンシなど）を定義し、PASS/FAIL を出力。
  - 各種クエリは存在しないテーブルに対して sqlite3.OperationalError をハンドリングし N/A を返す安全設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations
- News NLP モジュールは OpenAI API に依存するため、API の利用制限やコストに留意してください。API キー管理は環境変数か引数で行います。
- Portfolio の position sizing は現状全銘柄共通の lot_size（デフォルト100）を前提としています。将来的に銘柄毎の単元対応が必要。
- 一部の価格欠損時（price 0.0）の扱いが保守的であり、将来的に前日終値などのフォールバックを導入する余地があります（TODO コメントあり）。
- set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでスキップされるため、運用環境で意図どおり動作するか事前検証を推奨します。
- run_monitoring は監視 DB に本番の sqlite_path を常に使用する設計のため、テスト実行時は注意が必要。

---

（今後のリリースでは変更点を日付順に追記してください。）
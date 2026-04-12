CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日（リポジトリ内の初期バージョン情報 __version__ を元にした想定日）です。

Unreleased
----------

- なし

0.1.0 - 2026-04-12
------------------

初回公開リリース。システム全体の主要コンポーネントを実装しました（モニタリング、実行エンジン、ポートフォリオ構築、ファクター計算、ニュース NLP、ユーティリティ、ツール等）。

Added
-----

- 全般
  - パッケージ初期版を追加。パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)。
  - DuckDB / SQLite を利用するデータパイプラインの基盤を実装（デフォルトデータパスを含む）。
  - パッケージ内モジュールを適切にエクスポート（kabusys.research, kabusys.portfolio などの __all__ を設定）。

- 設定管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。
  - .env/.env.local の読み込みルールを実装（OS 環境変数の保護、override の制御、読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - .env ファイルの行パーサを実装し、export プレフィックスやシングル/ダブルクォート、インラインコメント、エスケープに対応。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視 / システム関連の環境変数をプロパティとして提供。
  - PAPER_FILL_MODE の検証（instant|partial|never|reject）、PAPER_TRADING_SQLITE_PATH 等の paper_trading 用分離設定を実装。
  - KABUSYS_ENV の有効値 (development, paper_trading, live) と LOG_LEVEL の検証を導入。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合に専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ポーリング起動スクリプト run_monitoring.py を追加。
    - SystemMonitor を初期化し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を "high" に設定。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しで監視用テーブルが存在することを保証（冪等処理）。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（警告）。
  - セクター集中・レジーム調整（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market_regime に基づいた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3。未知は 1.0 でフォールバック）。
  - 位置付けサイズ計算（position_sizing）
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応し、単元株（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリングを実装。
    - スケールダウン時には端数処理（lot 単位での残差を考慮して追加配分）を行い再現性を確保。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクターを DuckDB 上の prices_daily / raw_financials を参照して計算。
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金・出来高比等。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリーを実装。
    - calc_forward_returns: 複数ホライズンに対応し、入力検証（horizons 範囲）を実施。
    - calc_ic / rank / factor_summary: ランク計算（同順位は平均ランク）、IC 計算（有効レコード 3 件未満で None）、各列の count/mean/std/min/max/median を算出。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - OpenAI (gpt-4o-mini) を用いたニュース記事のセンチメントスコアリング機能を実装。
  - 処理概要:
    - target_date に基づくニュースウィンドウ計算（JST→UTC の変換を考慮）。
    - raw_news と news_symbols を用いて銘柄ごとに記事集約（最大記事数・文字数でトリム）。
    - 最大 20 銘柄単位でバッチ送信（JSON Mode）、429 / ネットワーク / 5xx に対する指数バックオフによるリトライ。
    - レスポンスのバリデーション・スコアの ±1.0 クリップ。
    - 成功した銘柄分のみ ai_scores テーブルに差分で書き込み（DELETE → INSERT 相当の置換）。
  - OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポートジェネレータを追加。
    - コマンドライン引数 --from / --to / --db に対応。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、SQLite ファイル存在チェックを実装。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 検証閾値（稼働率 99% 等）をスクリプタブル定数として定義。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プラットフォーム差分を吸収したプロセス優先度設定を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
  - アクセス権限や未サポート環境に対するフォールバック（警告ログ）を実装。

Changed
-------

- 初回リリースのため該当なし。

Fixed
-----

- 初回リリースのため該当なし。

Security
--------

- OpenAI API キー等の機密情報は環境変数経由で管理することを想定。README/.env.example による運用を推奨（未実装のドキュメント参照）。

Notes / Usage hints
-------------------

- 環境設定:
  - 自動 .env ロードはデフォルトで有効。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須の環境変数は Settings のプロパティで参照され、未設定時は ValueError を発生させます（起動時に早期検出）。

- Paper Trading:
  - KABUSYS_ENV=paper_trading を指定すると、発注系は paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
  - PAPER_FILL_MODE によって MockBroker の約定挙動を制御できます（instant|partial|never|reject）。

- 監視:
  - run_monitoring.py は MONITOR_POLL_INTERVAL（秒）でポーリング間隔を制御できます。不正な値（0 以下や非整数）はデフォルト（60 秒）にフォールバックします。
  - 監視は常に本番 sqlite_path を参照する設計です（環境に依存しない）。

- 実行環境優先度:
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限がない場合は警告を出してスキップします。

- DuckDB / SQLite:
  - 解析・研究用途は DuckDB を用いた SQL 集約を前提としています。prices_daily / raw_financials 等のスキーマに依存します。

今後の改善候補（抜粋）
---------------------

- position_sizing の価格欠損時のフォールバック価格（前日終値や取得原価）を追加してエクスポージャーの過小評価を防ぐ。
- stocks マスタに lot_size を持たせ、銘柄ごとの単元対応を行う。
- AI スコアリングの永続化・部分失敗時のより強固なロールバック戦略や観測性の向上（ログ・メトリクス）。
- テスト・CI の充実（各関数の単体テスト、DB モック等）。

-----------

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やドキュメントがある場合は、それに合わせて修正してください。
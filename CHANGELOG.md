CHANGELOG
=========

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

注意: ここに記載した内容はソースコードから推測してまとめたものであり、実際のリリースノートやドキュメントと若干の差異があり得ます。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース。KabuSys の基礎機能群を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行系 / デーモン起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 環境変数 KABUSYS_ENV が "paper_trading" の場合は paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを作成（実運用/モックの切替を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等のコンポーネントを組み立ててセッション実行。
    - 起動時にプロセス優先度を "high" に設定するユーティリティを呼び出す。
    - DuckDB と SQLite 両方の接続を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログとともにデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順: OS環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env のパースは quote やエスケープ、コメント（'#'）処理に対応。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 / PID・kill flag など）。
    - 値検証を行い不正値は ValueError で通知（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - settings インスタンスをモジュールレベルで提供。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)：スコア降順、同点は signal_rank でブレーク。
    - 重み計算：等分配 (calc_equal_weights)、スコア加重 (calc_score_weights)（全銘柄スコアが 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)：既存保有のセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外。
    - レジーム乗数 (calc_regime_multiplier)：regime ("bull"/"neutral"/"bear") に応じて投下資金乗数を返却（未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 (calc_position_sizes)
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）丸め、per-stock および aggregate cap、cost_buffer による保守的見積り、スケーリングと残差配分アルゴリズムを実装。
      - price 欠損や 0 値の取り扱いに注意したログ出力あり。
- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算関数を追加。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルのみ参照する設計。
    - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を計算。
    - ウィンドウサイズや不足データに対する None ハンドリングを実装。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)
    - IC（Information Coefficient）計算 (calc_ic)
    - ランク変換ユーティリティ (rank) とファクター統計サマリー (factor_summary)
    - 外部ライブラリに依存しない純粋 Python 実装。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄毎に記事を集約し OpenAI（gpt-4o-mini）でセンチメントをスコア化、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大対策（記事数・文字数の上限）、レスポンスバリデーション、スコア ±1.0 のクリップ、部分更新戦略（コード絞り込み）を実装。
    - 429・ネットワーク障害・5xx 等に対する指数バックオフのリトライロジック、API キー未設定時の ValueError。
    - タイムウィンドウ計算（JST ベースを UTC に変換）やフェイルセーフ設計（API 失敗時はスキップして継続）を採用。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度設定を提供（Windows と POSIX 対応）。
    - set_process_priority(level)（high/normal/low）、set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応 OS 時は警告ログでスキップ。
- ツール
  - tools/paper_verification_report.py
    - paper_trading DB を解析してレポートを標準出力に出力する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。閾値はソースコード内で定義（例: 稼働率 >= 99%、P95 <= 200 ms）。
    - 日付フィルタ、DB パス引数をサポート。
- パッケージ初期化とエクスポート
  - kabusys/__init__.py によるバージョン定義と主要サブパッケージの __all__ 定義。
  - research パッケージ __all__ に主要関数をエクスポート。
  - portfolio パッケージで主要関数を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- run_monitoring と run_execution において、DB 接続を finally ブロックで確実にクローズするよう実装（リソースリーク抑止）。

Notes / Implementation details
- DB: SQLite（monitoring / paper_trading）と DuckDB（時系列・ファクタ処理）を併用する設計。監視データは monitoring DB、価格・財務等は DuckDB を想定。
- 設定検証: env 値の不正は ValueError を送出するため、起動前に .env.example を整備し適切に設定する必要あり。
- 失敗許容設計: AI スコア取得や監視チェックで一部失敗してもサービス継続するように設計（ログ出力・スキップ）。
- パフォーマンス考慮: DuckDB のウィンドウ関数を多用し一括クエリで計算する等、データ量を考慮した実装になっている。

今後の改善案（ソースから推測）
- lot_size を銘柄別に持たせるための stocks マスタ導入（コメントに TODO が存在）。
- apply_sector_cap の価格欠損時のフォールバックロジック（前日終値等）の追加。
- ai/news_nlp の部分処理失敗時のリトライ・部分ロールバック戦略の強化。
- unit tests / integration tests の追加（現状は設計ドキュメントや docstring に多く依存）。

ライセンスや著作権等の情報はソースツリー内のドキュメントを参照してください。
# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（現時点の作業中の変更はここに記載します）

## [0.1.0] - 2026-04-17
初回リリース。主要な機能群と実装の概要を以下に示します。

### 追加（Added）
- 全体
  - パッケージ初期リリース。自動売買システム "KabuSys" のコアモジュールを提供。
  - __version__ を 0.1.0 に設定。

- 実行・監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じてブローカークライアントを生成し、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度を起動時に設定。

- 設定管理
  - config.py: 環境変数 / .env ファイルを自動読み込みする Settings クラスを提供。
    - プロジェクトルートの検出（.git または pyproject.toml を基準）により、CWD に依存せず .env をロード。
    - .env/.env.local の読み込み優先順位を実装（OS 環境変数を保護）。
    - 詳細なパースロジックを実装し、export 形式、クォート、インラインコメント等に対応。
    - 各種設定プロパティ（DB パス、PID ファイル、監視閾値、PAPER_TRADING の切替等）を提供。
    - 入力値チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装し、不正値はエラーに。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレーク（signal_rank）による候補選定。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア正規化による重み算出（スコア全部 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の適用（既存保有の時価ベースで判定）。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告とともにフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。単元株（lot_size）で丸め、全体投資額が利用可能現金を超えた場合はスケールダウンして lot 単位で再配分するロジック（cost_buffer を考慮）。

- 研究・リサーチ
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算。MA200、ATR、各種リターン等を算出。
  - research/feature_exploration.py:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得するクエリを実装。
    - calc_ic, rank, factor_summary: スピアマン IC（ランク相関）、ランク付け（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research パッケージ __all__ で主要関数群を公開。

- AI / ニュース
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄単位の ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx 用の指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）等を設計。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。
    - API キー未設定時は明示的なエラーを返す。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。SQLite（デフォルト data/paper_trading.db）から
      - システム稼働率（system_status）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下件数（risk_logs）
      - レイテンシ（P95 等）
      を集計し、合否判定（閾値はソース内で定義）を標準出力に出力。CLI オプションで期間指定・DB 指定可能。

- ユーティリティ
  - utils/process_priority.py:
    - cross-platform（Windows / POSIX）でプロセス優先度を設定する set_process_priority を提供。set_cpu_affinity により CPU affinity を最初の N コアに固定するユーティリティも追加。権限不足や未対応 OS では安全にスキップする実装。

- DB 接続
  - モジュールで sqlite3 と DuckDB を併用。monitoring 用のテーブル初期化ユーティリティ（init_monitoring_db）呼び出しを起動スクリプトで行い、監視テーブルの存在を保証（冪等）。

### 変更（Changed）
- run_monitoring: 監視プロセスは環境（KABUSYS_ENV）にかかわらず、本番用 sqlite_path を使用するように明示（モニタリングは常に本番データを参照）。
- Settings: .env 自動読み込みのデフォルト動作を実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み順序は OS 環境 > .env.local > .env。
- ポートフォリオ関連: position_sizing の aggregate cap 処理における端数処理と残余配分（lot 単位での再分配）を実装し、利用可能現金に収める振る舞いを厳密化。
- research/feature_exploration.rank: 丸め（round(..., 12)）により浮動小数の丸め誤差での ties 検出漏れを回避するように改善。

### 修正（Fixed）
- config._parse_env_line:
  - export キーワード、クォート文字、バックスラッシュエスケープ、インラインコメントの扱いをより厳密に実装し、.env のパース精度を向上。
- run_monitoring._get_poll_interval:
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）を検出してデフォルトにフォールバックし、time.sleep に渡す際の ValueError を回避。
- research/factor_research.calc_momentum / calc_volatility / calc_value:
  - データ不足時に None を返すことで downstream 処理での NULL 安全性を確保。
- tools/paper_verification_report:
  - 各クエリ実行時に sqlite3.OperationalError を捕捉して、テーブル未存在などのケースでもレポート処理が継続するように堅牢化。
- utils/process_priority:
  - 未対応 OS や権限不足時に例外を投げず警告ログでスキップするよう改良。

### セキュリティ（Security）
- ai/news_nlp の OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）から取得し、未設定時は ValueError を送出することでキー未設定の誤動作を防止。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

### 注意・既知事項（Notes / Known issues）
- ai/news_nlp.py は設計に基づく堅牢化を行っているものの、実際の OpenAI レスポンス形式に対する追加のバリデーションやモデル変更時の互換性確認を推奨します。
- position_sizing の単元株数は現状グローバルな lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map を導入することをTODOとして記載。
- run_monitoring は監視 DB に本番 sqlite_path を使用するため、テスト時には環境変数で明示的にパスを切り替えるか、プロジェクト構成上で isolation を行ってください。
- news_nlp ファイルが大きいため一部の補助関数（_fetch_articles 等）の実装継続が必要（コードベース上で未完の箇所がないか確認してください）。

---

作成: KabuSys チーム（ソースコードから推測してまとめました）。各項目の詳細・正確な影響範囲はソースコードの該当箇所をご参照ください。
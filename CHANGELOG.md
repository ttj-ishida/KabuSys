# CHANGELOG

すべての重要な変更点を「Keep a Changelog」準拠の形式で日本語で記載します。  
（コードベースの内容から推測して記載しています）

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初期実装を追加
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン情報（0.1.0）と公開 API を定義。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `.env` パース機能を強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
    - 必須環境変数取得ヘルパ `_require()` と Settings クラスを提供。DBパスやPaper Trading用設定、監視閾値、ログレベル、環境（development/paper_trading/live）判定などをプロパティで取得可能。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等のデフォルト管理。
- 実行・監視用起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 DB に完全分離して動作。Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドでの実行、停止フラグ対応を実装。
    - プロセス優先度を起動時に設定（High）。
    - stop フラグ（data/stop_requested.flag）と PID ファイルの扱い。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。監視は環境にかかわらず本番 sqlite_path を使用（意図的に分離）。
    - 監視停止フラグ検知時の安全終了、check_once() での例外キャッチとログ。
- 監視 DB 初期化呼び出し（init_monitoring_db を両スクリプトで利用）
  - 監視テーブルの存在保証（冪等）。
- Execution 周りのコンポーネント（参照・組み立てポイント）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など（スクリプト側での組み立てと設定）。
  - RiskConfig のデフォルトパラメータ（max_position_pct 等）、初期資金取得に broker.get_available_cash() を使用。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定 set_process_priority(level) を実装（Windows / POSIX 対応）。権限不足や未対応OS時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定）。不正引数や権限不足時は安全にスキップ。
- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。スコア全0時は等配分へフォールバック（警告ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。既存ポジションのセクター別エクスポージャ計算、売却予定銘柄の除外、"unknown" セクターの扱いなど。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知のレジームは警告して1.0にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）。単元（lot_size）での丸め、per-position と aggregate cap の両方を考慮したスケーリング、cost_buffer による保守的見積り、残余キャッシュによる端数配分アルゴリズムを実装。
  - src/kabusys/portfolio/__init__.py で主要関数を公開。
- 研究・リサーチ関係
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算。MA200・ATR 等のウィンドウ長やスキャン日数など定数を定義。
    - 欠損データ時の None 扱いや最小データ件数チェックを実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリー（factor_summary）。外部依存を使わない純粋実装。
    - calc_ic は有効レコードが3件未満の場合 None を返す等の安全策。
  - src/kabusys/research/__init__.py で公開 API をまとめる（zscore_normalize を data.stats から再公開）。
- AI ニュース NLP（下地実装）
  - src/kabusys/ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でスコアリングして ai_scores へ書き込む設計。ターゲットウィンドウの時間計算、記事集約の制限（記事数・文字数）、バッチ処理（最大20銘柄/回）、リトライ（429/ネットワーク/5xx の指数バックオフ）、結果バリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（削除→挿入の範囲限定）などフェイルセーフを備えた設計。
    - OPENAI_API_KEY の解決を実装。calc_news_window 関数などユーティリティを提供。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）等の指標を集計し、PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率99%など）。
    - CLI 引数 --from / --to / --db をサポート。DB が存在しない場合のエラーメッセージと安全な sqlite3.OperationalError のハンドリングを実装。

### 変更 (Changed)
- 起動スクリプト共通の振る舞いとポリシー
  - 監視（run_monitoring.py）は KABUSYS_ENV に依存せず本番の sqlite_path を使用する実装に（監視データの一元管理を意図）。
  - Execution エンジンは paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離（Paper Trading の完全分離を明確化）。
- 環境変数読み込みの優先順位と保護
  - OS 環境変数を保護して .env.local の上書きを制御（override のフラグと protected セットによる保護）。
- ロギングと安全シャットダウン
  - run_monitoring/run_execution が停止フラグや KeyboardInterrupt を検知して安全にリソースを解放するよう改善。
- デフォルト値と検証の強化
  - MONITOR_POLL_INTERVAL の入力検証（0以下や非整数の入力は警告してデフォルトにフォールバック）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力値検証を Settings プロパティで厳密化。

### 修正 (Fixed)
- 複数の境界ケースでの安全化および例外処理追加
  - DuckDB / SQLite クエリ実行時の OperationalError に対するフォールバック（レポート生成などで安全に N/A を返す）。
  - process_priority や cpu_affinity の呼び出しで権限不足や未対応環境発生時に例外を握りつぶして警告する実装に（起動失敗を防止）。
  - portfolio.calc_score_weights: 全スコアが 0.0 の場合にゼロ除算を防ぎ等分配へフォールバック。
  - research.feature_exploration.rank: 同順位の平均ランク処理（ties）を正しく扱う実装。

### セキュリティ (Security)
- OpenAI API キーの取り扱いは環境変数または引数で明示的に渡す設計。未設定時は ValueError を送出して明示的に失敗するようにし、キーが流出しにくい運用を想定。

---

注記:
- 上記はソースコード構成とコメントから推測した初期リリースの変更履歴です。実際のリリースノートには実装の細部・既知の制限・マイグレーション手順（データベーススキーマ等）が含まれることが望ましいです。必要であれば各モジュール別の詳細な変更点や既知の問題一覧も作成します。
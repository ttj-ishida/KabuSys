Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

Unreleased
---------

- （今後の変更をここに記載）

0.1.0 - 2026-04-12
------------------

Added
- 初期リリース: KabuSys パッケージ（バージョン 0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0" を追加。

- 設定管理 (kabusys.config.Settings)
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env / .env.local の読み込み順序と上書きルールを実装（OS 環境変数保護）。
  - 複雑な .env パース対応:
    - export プレフィックス対応、クォート文字とバックスラッシュエスケープ処理、
    - インラインコメントの取り扱い（クォート有無に応じたルール）。
  - 環境変数必須チェック用 _require()、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 各種設定プロパティ（DBパス、PID/kill フラグ、閾値、PAPER_FILL_MODE 等）を提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）。

- 実行/監視スクリプト
  - run_execution.py:
    - ExecutionEngine 起動エントリポイント。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite を使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行。
    - RiskManager に対するデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - duckdb 接続を利用。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する旨の挙動（意図的な設計）。
    - duckdb との併用、プロセス優先度設定。

- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db を各起動スクリプトから呼び出し、監視用テーブルが存在することを冪等的に保証。

- ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）差分吸収済みの優先度設定。
    - Windows 用定数、POSIX 用 nice 値を用意。
    - 設定失敗時は警告ログでフォールバック。
  - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留めする機能、引数検証と例外処理を実装。

- ポートフォリオ組成 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレーク（signal_rank）で上位 N 件抽出。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じて発注株数を計算。
    - 単元株（lot_size）丸め、max_position_pct／max_utilization／cost_buffer を考慮した aggregate cap スケーリング。
    - スケーリング時に小数端数を lot 単位で再配分するロジック（残差順で追加配分）。
    - 価格欠損時のスキップやデバッグログ。

- リサーチ/ファクター (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily/raw_financials テーブルを参照して各種ファクターを計算（MA200, ATR20, リターン等）。
    - 欠損データやウィンドウ不足時の None ハンドリング。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得。
    - calc_ic: スピアマンランク相関 (IC) を実装（ランク処理に ties の平均ランク処理を含む）。有効レコード数が少ない場合は None。
    - rank / factor_summary: ランク変換、基礎統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装（pandas 非依存）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - ニュース記事を OpenAI (gpt-4o-mini) に送って銘柄ごとにセンチメントスコアを算出し、ai_scores テーブルへ書き込む機能を提供。
  - 処理フロー:
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用）。
    - 記事集約（1 銘柄あたり記事数・文字数上限でトリム）。
    - 最大 20 銘柄のバッチ送信、429/ネットワーク/5xx などで指数バックオフによるリトライ実装（最大リトライ回数あり）。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - 部分失敗時の既存スコア保護のため、対象コードのみを削除してから挿入する安全な書き換え戦略。
  - OpenAI API キー未設定時は ValueError を送出。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成スクリプトを提供（CLI）。
  - レポート指標:
    - 稼働率（system_status）／注文成功率（trade_logs の Created/Filled/Sent 集計）／リスク却下数（risk_logs）／API レイテンシ（avg/max/P95）など。
  - P95 計算ユーティリティ、日付フィルタの WHERE 句ビルド、SQL 実行の OperationalError に対するフォールバックを実装。
  - CLI オプション: --from, --to, --db。PAPER_TRADING_SQLITE_PATH 環境変数との解決ルール。
  - 判定基準（閾値）と PASS/FAIL 判定ロジックを実装。

Changed
- （初回リリースのため履歴なし）

Fixed
- .env パーサー: クォート内部のバックスラッシュエスケープやインラインコメント処理を改善し、より堅牢に。
- モジュール群で DB テーブル欠如や OperationalError 発生時にフォールバックするようにし、ツールやレポートが DB 欠損でも致命的にならないよう耐性を追加。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY か関数引数で明示的に供給する設計（未設定時は明確にエラーを出す）。

Notes / Implementation details
- DuckDB を分析用途（prices_daily / raw_financials）に使用。発注処理用データは sqlite（monitoring/paper_trading）で管理する構成。
- Paper Trading は本番 DB と明確に分離され、設定によって専用 SQLite ファイルへ書き込む。
- 実装は外部依存（pandas など）に頼らず、標準ライブラリ + duckdb + psutil + openai を中心に設計。

Authors
- KabuSys 開発チーム（コードの docstring とファイル構成に基づく推定）

---

注: 上記は提供されたソースコードの内容と docstring から推測してまとめた CHANGELOG です。実際のコミット履歴やバージョン管理ログが存在する場合は、そちらを優先して正確な差分を反映してください。
CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

なお、以下の内容はコードベースから推測して記載しています（実装済み機能や挙動の要約）。

v0.1.0 - 2026-04-13
-------------------

Added
- 初期リリース: KabuSys パッケージ v0.1.0 を公開。
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立て、ExecutionEngine.run_session() で取引セッションを実行。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを含む。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を組み込み。
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用する旨の挙動を明示。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 / DuckDB 接続を確立し、SystemMonitor.check_once() を定期実行。
- 設定管理
  - config.py: 環境変数/.env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装（export 形式、引用符付き値のエスケープ、インラインコメント処理を考慮）。
    - Settings クラスを提供し、各種設定 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_* 等) をプロパティとして提供。
    - DB/監視/システム関連設定をプロパティで取得可能: duckdb_path / sqlite_path / paper_sqlite_path / pid_file_path / kill_flag_path / kill_flag_clear_on_start / CPU/MEM/DISK 閾値等。
    - paper_fill_mode を実装（有効値: "instant" | "partial" | "never" | "reject"。不正値は ValueError を送出）。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live のみ許容）。
- ポートフォリオ構築
  - portfolio_builder.py: 銘柄選定・重み計算ユーティリティを追加。
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補抽出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装（スコア合計が 0 の場合は等配分へフォールバックし警告）。
  - risk_adjustment.py: セクター集中制限・レジーム乗数を実装。
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき新規候補を除外。sell_codes（当日売却予定銘柄）の除外に対応。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告の上 1.0 でフォールバック。
  - position_sizing.py: 発注株数計算・リスク制限・単元丸めを実装。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元 (lot_size) 切り捨て・aggregate cap によるスケールダウン（cost_buffer を考慮）、端数配分ロジックを実装。
- 研究系
  - research/factor_research.py: DuckDB を用いたファクター計算を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（データ不足時は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算。
    - calc_value: per / roe を raw_financials と prices_daily から計算。
  - research/feature_exploration.py: 将来リターン計算・IC・統計サマリー等を実装。
    - calc_forward_returns: LEAD を使って複数ホライズンの将来リターンを一括取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（ランクは同位は平均ランク）を実装。有効レコード数 < 3 で None を返す。
    - factor_summary, rank: 基本統計量とランク付けユーティリティを提供。
  - research/__init__.py: 主要関数をエクスポート（zscore_normalize を含む）。
- AI / ニューススコアリング
  - ai/news_nlp.py: raw_news → OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリングを実装。
    - ニュース取得ウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST、内部は UTC naive datetime）。
    - 1 銘柄あたり記事数と文字数の上限（記事数=10、文字数=3000）でトリム。
    - 最大 20 銘柄 / バッチで API 送信、429/ネットワーク/5xx に対する指数バックオフリトライ（上限 3 回）。
    - レスポンスの厳密な JSON バリデーション、スコアを ±1.0 にクリップ。
    - 成功チャンク分のみ ai_scores テーブルに置換更新（部分失敗時に他銘柄スコアを保護）。
    - OpenAI API キー未設定時は ValueError を送出。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - CLI 引数: --from / --to / --db。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算し、定められた閾値（稼働率 99% 等）で PASS/FAIL 判定を出力。
    - DuckDB / SQLite のテーブル欠如時に例外を回避して N/A 扱いとするフェイルセーフ実装。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収。権限不足や未サポート OS の場合は警告を出してスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OpenAI 等）は環境変数で管理し、未設定時は明示的にエラーを返す実装になっている点を明記。

Notes / Breaking changes / 注意点
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず sqlite_path（本番向けのパス）を使用します。テスト/ペーパー用 DB と分離したい場合は設計に注意してください。
- Paper Trading 実行 (run_execution) は is_paper 判定時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH で上書き可）を使用してデータ分離を確保しています。
- .env 自動読み込みはデフォルトで有効（プロジェクトルートが検出できない場合はスキップ）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_fill_mode の不正値は ValueError を送出するため、環境変数設定ミスで起動時に例外となる可能性があります。
- MONITOR_POLL_INTERVAL は整数のポーリング間隔を期待します。不正値や 0 以下はデフォルト (60 秒) にフォールバックして警告を出します。
- OpenAI へのリクエストでは JSON の厳密な出力を期待しており、外部 API の応答フォーマット変更に弱い可能性があります。エラーはログに出力して処理を継続する設計になっています。

Usage examples（抜粋）
- 監視起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db または PAPER_TRADING_SQLITE_PATH で DB パスを指定

今後の改善アイデア（コードから推測）
- position_sizing の価格欠損時のフォールバック（前日終値など）を実装。
- apply_sector_cap の "unknown" セクター取り扱いや price の欠損対策の強化。
- ai/news_nlp の部分失敗時の再実行・監査ログ強化。
- duckdb の書き込み/トランザクション戦略や大規模データ処理の性能最適化。

参考: パッケージバージョン
- 現在のパッケージバージョンは __version__ = "0.1.0"（src/kabusys/__init__.py）。

以上。
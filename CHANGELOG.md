CHANGELOG.md
=============

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

リリースの方針:
- セマンティックバージョニングに準拠します（MAJOR.MINOR.PATCH）。
- ここに記載のない内部実装の微細な変更は省略します。

Unreleased
----------
- なし

[0.1.0] - 2026-04-13
--------------------
初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装しています。主な追加内容は以下のとおりです。

Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を定義（portfolio, research, execution, monitoring 等の主要関数・モジュールをエクスポート）。

- 設定管理
  - 環境変数/`.env` 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - `.env` パーサを実装（コメント、クォート、export 形式に対応）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスで豊富な設定プロパティを提供:
    - J-Quants / kabu API / LINE API / DB パス（duckdb/sqlite）/PID・kill フラグパス等。
    - PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（instant/partial/never/reject）等の paper_trading 用設定。
    - 許容閾値（CPU/MEMORY/DISK）や環境（development/paper_trading/live）の検証。

- 実行/監視スクリプト
  - run_execution.py:
    - プロセス優先度を設定して実行コンポーネントを組み立て、ExecutionEngine を起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、EngineConfig の初期化。
    - 監視テーブルの初期化（init_monitoring_db）を冪等に実行。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出してデフォルトにフォールバック。
    - 監視用途は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を高優先度に設定してから起動。

- 実行ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（"high"/"normal"/"low"）と CPU affinity 設定を行うユーティリティを追加。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収。権限不足等は警告ログでスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - buy シグナルの候補選定（score 降順、signal_rank によるタイブレーク）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）で全スコアがゼロの場合は等分配にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap（既存保有のセクター比率が上限を超える場合に新規候補を除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知のレジームは警告と共に 1.0 をフォールバック）。
  - portfolio/position_sizing.py:
    - ポジションサイズ計算 calc_position_sizes を実装（allocation_method: "risk_based" | "equal" | "score"）。
    - risk_based：risk_pct と stop_loss_pct を用いた株数算出。
    - equal/score：ウェイトに基づく割当。lot_size（単元）丸め、単銘柄上限(max_position_pct)、aggregate cap（available_cash）に基づくスケーリング（余剰キャッシュによる再配分ロジック含む）。
    - cost_buffer による保守的コスト見積り（スリッページ・手数料を想定）。

- Research（因子計算・解析）
  - research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20、ATR_pct、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を追加。
    - データ不足時の None 扱い、ウィンドウ幅とスキャン範囲を調整して週末・祝日を吸収。
  - research/feature_exploration.py:
    - 将来リターン calc_forward_returns（複数ホライズンをまとめて取得する SQL）、IC（Spearman の ρ）を計算する calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部ライブラリに依存せず、標準ライブラリと DuckDB で実現。
  - research/__init__.py で主要関数と zscore_normalize をエクスポート。

- AI（ニュース NLP）
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を銘柄ごとに算出して ai_scores テーブルへ書き込むロジックを追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ送信（最大 _BATCH_SIZE=20）、記事数/文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアを ±1.0 にクリップ。
    - API キー解決は引数優先、未設定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数。
    - しきい値（稼働率>=99.0%、fill_rate>=90%、send_rate>=95%、P95<=200 ms）による PASS/FAIL 判定。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。DB 存在チェックとエラーハンドリングあり。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- DuckDB を集計・因子計算の主要 DB として使用。prices_daily / raw_financials テーブルに依存する実装が多い。
- SQLite は monitoring/trade_logs/risk_logs などのイベントログや paper_trading 用の記録に利用される。
- 実行時のプロセス優先度設定・PIDファイル管理・kill フラグ等、運用監視に配慮した設計。
- 外部 API 呼び出し（kabu API、OpenAI 等）は環境変数でキーやエンドポイントを設定する想定。Paper trading モードでの完全分離をサポート。

今後の予定（例）
- 銘柄ごとの lot_size をマスタで持つ拡張（position_sizing の TODO）。
- news_nlp の部分失敗時のより細かいロールバック/トランザクション戦略。
- ユニットテスト・統合テストの拡充（特に DuckDB クエリの回帰検証）。

---

この CHANGELOG はコードベースから推測して作成しています。詳細な仕様やリリース方針に合わせて追記・修正してください。
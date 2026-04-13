# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースは SemVer を想定します。

なお、本 CHANGELOG は提供されたコードベースから機能・仕様を推測して作成しています。

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。

### 追加 (Added)
- パッケージの基本情報
  - kabusys パッケージを追加。バージョンを __version__ = "0.1.0" として定義。

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - BrokerClientFactory に基づき、本番／Paper Trading のクライアント切替に対応。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は専用 SQLite DB（data/paper_trading.db がデフォルト）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを実施。
    - DB 初期化（監視テーブルの冪等な作成）と DuckDB 接続を行い、ExecutionEngine.run_session() を呼ぶ。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使う設計（監視は本番データ参照を想定）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env / .env.local 自動読み込み（OS 環境変数が優先、.env.local は .env を上書きする）。プロジェクトルートは .git または pyproject.toml で探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能（テスト用）。
    - .env 行パーサは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入し、環境変数をプロパティとして安全に取得（必須変数チェック、値検証）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグ等の設定プロパティを用意。
    - PAPER_FILL_MODE（paper trading の約定モード）を検証して取得。
    - KABUSYS_ENV 値検証（development / paper_trading / live）。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）を実装。Windows と POSIX(Linux, macOS, FreeBSD) を考慮。
    - CPU affinity 設定関数（set_cpu_affinity）を追加。
    - psutil 例外を適切にハンドリングし、権限不足などの際は警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等分配へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有時価ベースで計算）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知レジームは警告のうえ 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を用いた保守的見積り、端数処理の再配分アルゴリズムを含む。

  - package export を __init__ で整理（select_candidates 等の再エクスポート）。

- 研究（Research）モジュール
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装。DuckDB の prices_daily / raw_financials を参照して SQL で計算。
    - 実装例: mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等。
    - データ不足時は None を返す設計。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、列の基本統計量集計（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - 外部ライブラリに依存しない純粋 Python 実装。入力検証（horizons 範囲等）あり。

  - research/__init__.py に主要 API をエクスポート（zscore_normalize を data.stats から含む）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。コマンドライン引数から期間フィルタ（--from / --to）と DB パス（--db）を指定可能。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 などを算出・出力。
    - PASS/FAIL 判定の基準値を定義し、詳細レポートを標準出力へ出力。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約して OpenAI API (gpt-4o-mini) により銘柄ごとのセンチメント（-1.0〜1.0）を取得し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）とバッチ（最大 20 銘柄）送信、トークン肥大化対策（1銘柄あたり最大記事数・文字数制限）を実装。
    - 429 / ネットワーク断 / 5xx 等に対して指数バックオフでリトライ、レスポンス検証、スコアクリップ、部分失敗時の既存スコア保護（対象コードで限定した DELETE → INSERT）を意図した処理を実装。

- DB 統合
  - sqlite3 を監視・発注ログ保存に使用、DuckDB をリサーチ・ファクター計算に使用する設計を導入。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を呼び出すことで監視用テーブルの存在を保証（冪等）。

### 変更 (Changed)
- なし（初回リリースのため変更履歴なし）。ただし各モジュールに実装上のデザインメモや TODO コメントあり。

### 修正 (Fixed)
- なし（初回リリース）。

### 破壊的変更 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出して明示的に扱うように設計。

---

注記:
- 本 CHANGELOG は提供されたソースコードの静的解析とコメントから機能を推測して作成しています。実際のリポジトリの履歴（コミット単位の差分）に基づくものではありません。
- 将来のリリースではユニットテスト追加、エラーハンドリング強化、外部設定（銘柄ごとの lot_size 等）拡張、パフォーマンス最適化（DuckDB クエリのチューニング）などが想定されます。
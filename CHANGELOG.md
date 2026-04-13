# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。日付はコードベースから推測した初期リリース日を設定しています。

## [Unreleased]

- 開発中の変更や調整がある場合はここに追記してください。

## [0.1.0] - 2026-04-13

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
  - Python パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 起動 / 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV に応じて本番/ペーパーを切り分け（paper_trading 時は専用 SQLite DB に記録）。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - プロセス優先度を起動直後に設定し（高優先度）、DB（SQLite / DuckDB）ハンドルの確実なクローズを実装。
    - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - check_once() 実行時の例外を捕捉してログ出力しループ継続する堅牢化を実装。
    - KeyboardInterrupt のハンドリングと DB クローズ処理を実装。

- 設定管理
  - config.py: 環境変数 / .env の読み込み・管理を実装。
    - プロジェクトルートを .git または pyproject.toml から検出して自動で .env / .env.local を読み込む機能を追加（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB パス /監視設定 / システム設定 等をプロパティとして取得できるようにした。
    - 入力値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
    - paper_trading 用のデフォルト DB パス（data/paper_trading.db）とその他の経路（PID ファイル、kill flag、しきい値）を定義。

- モニタリング / ツール
  - monitoring_db 初期化を呼ぶ箇所を各起動スクリプトに導入（冪等）。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などの指標を計算して表示。
    - 日付フィルタのサポート（--from / --to / --db オプション）。
    - P95 計算、SQL 実行での OperationalError のフォールバック処理、閾値による PASS/FAIL 判定を実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - シグナルの並び替え（score 降順、signal_rankでのタイブレーク）、候補選択関数 select_candidates を実装。
    - 等分配 calc_equal_weights、スコア重み calc_score_weights（全スコアが 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有を考慮し特定セクターが上限を超える場合に当該セクターの新規候補を除外）を実装。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を追加。未定義レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - 株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 損切り率・リスク率に基づく risk_based 計算、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash に対するスケールダウン）を実装。
    - cost_buffer を用いた保守的コスト見積り、余剰キャッシュを用いた端数処理（lot 単位で追加配分）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）などのファクター計算を追加。
    - DuckDB を用いた SQL クエリ実装で prices_daily / raw_financials テーブルを参照する設計。データ不足時は None を返す設計。
  - research/feature_exploration.py:
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman）calc_ic、rank ユーティリティ、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存しない純 Python 実装。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - ニュースウィンドウの明示的計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window。
    - バッチサイズ、最大記事数／文字数制限、429/ネットワーク/5xx に対する指数バックオフのリトライ方針を実装。
    - API キー解決（引数 or OPENAI_API_KEY 環境変数）、出力 JSON のバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象 code の限定 DELETE→INSERT）等を考慮。

- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差（Windows / POSIX）を吸収した set_process_priority(level) を実装（high/normal/low）。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は設定しない）。
    - psutil の権限エラー等を安全にハンドリングして警告ログを出す。

- パッケージ初期化
  - research/__init__.py / portfolio/__init__.py / tools/__init__.py / utils/__init__.py を追加して API をエクスポート。

### Changed
- .env の自動読み込みポリシーを明確化:
  - 読み込み順序は OS 環境 > .env.local > .env。
  - 既存 OS 環境変数は保護され、.env.local の override は protected を考慮して行われる。

### Fixed
- 起動処理および DB 接続後のクリーンアップ（finally での close）を徹底し、リソースリークのリスクを低減。

### Notes / Design decisions
- DuckDB を分析用途（prices_daily, raw_financials, ai_scores 等）に利用し、SQLite は監視・実行のトランザクション／ログ用途に使い分ける設計。
- 時刻・日付処理はルックアヘッドバイアス防止の観点から datetime.today()/date.today() を直接参照しない設計思想を採用（関数引数で date を受け取る）。
- 外部 API 呼び出し（ブローカー、OpenAI）はフェイルセーフ（エラー時はログを出して処理継続）を基本方針とする。

### Security
- 機密情報（API トークン等）は Settings 経由で環境変数から取得する設計。サンプル .env（.env.example）を参照する旨のメッセージを用意。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先して更新してください。
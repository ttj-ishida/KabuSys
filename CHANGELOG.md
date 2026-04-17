CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
日付はリリース日（YYYY-MM-DD）です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- プロジェクト初回公開リリース (v0.1.0)。
- 起動スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はリポジトリ直下の data/stop_requested.flag ファイルで検知。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全分離。停止フラグ・PID ファイル処理・デーモン実行ループを実装。
- 設定管理:
  - config.py: .env 自動読み込み機能を実装（.env, .env.local、OS 環境変数優先）。.git または pyproject.toml を基準にプロジェクトルートを特定。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード停止可能。export 付き行、クォート文字列、インラインコメントなどに対応する堅牢なパーサを実装。
  - Settings クラスを追加し、各種環境変数（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システムモード等）への型チェック・バリデーション・デフォルトを提供。PAPER_FILL_MODE の有効値チェックや KABUSYS_ENV / LOG_LEVEL の検証を行う。
- ユーティリティ:
  - process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、権限不足や未対応 OS の場合は警告ログでフォールバック。
- ポートフォリオ構築:
  - portfolio package:
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合のフォールバック警告を実装。
    - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。unknown セクター扱い・ログ出力等の仕様を明記。
    - position_sizing.py: 発注株数算出 (calc_position_sizes) を追加。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン（端数分配の再割当て）などを実装。cost_buffer による保守的見積りもサポート。
- リサーチ機能:
  - research package:
    - factor_research.py: Momentum / Volatility / Value ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出。
    - feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク変換ユーティリティ (rank) を追加。外部依存を用いず標準ライブラリで実装。
    - research.__init__ で zscore_normalize（kabusys.data.stats 由来）と主要関数をエクスポート。
- AI / ニュース:
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント解析し、銘柄別 ai_scores テーブルへ書き込む処理を追加。バッチ送信、チャンクサイズ制限、文字数上限、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）などを設計に含む。ニュース収集ウィンドウ（JST→UTC の変換）計算ユーティリティ calc_news_window を実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。コマンドラインから期間指定可能（--from / --to / --db）。system_status / trade_logs / risk_logs などの集計を行い、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を出力し、閾値を超えるかで PASS/FAIL を判定する。デフォルト閾値（稼働率 99%、注文成功率 90% 等）を定義。
- DB / 分析基盤:
  - 全体で DuckDB と SQLite を併用する設計を導入（prices_daily 等は DuckDB、監視/注文ログは SQLite を想定）。monitoring の初期化ユーティリティ init_monitoring_db 呼び出しを実装場所から呼択して DB テーブルの存在を保つ。
- パッケージ構成:
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。portfolio・research・ai などのサブパッケージを整理してエクスポートを整備。

Changed
- n/a（初回公開のため既存機能の変更履歴はありません）。

Fixed
- n/a（初回公開）。

Deprecated
- n/a

Security
- OpenAI API キーは外部にハードコードせず、api_key 引数または環境変数 OPENAI_API_KEY から取得する設計。未設定時は明確にエラーを出す仕様。

Notes / Known limitations / TODO
- ai/news_nlp.py: 実装は API 失敗時にフェイルセーフで継続する設計だが、外部 API 呼び出しのため実行環境での設定（OPENAI_API_KEY）が必須。
- position_sizing.calc_position_sizes: lot_size を銘柄別に対応するための拡張は TODO コメントとして残している（将来的に銘柄別 lot_map を受け取る設計を検討）。
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を使用する改善は将来対応予定（TODO）。
- config._find_project_root は .git または pyproject.toml を探索してプロジェクトルートを判断するため、配布環境でこれらが存在しない場合は自動 .env 読み込みをスキップする。
- run_monitoring は Monitoring 用 DB として常に settings.sqlite_path（本番 DB）を使用する仕様のため、監視データを分離したい場合は設定で sqlite_path を変更してください。

その他
- ログやエラー処理は基本的に警告ログや例外のキャッチで安全にフォールバックする方針で実装されています。実稼働導入時は各種閾値・設定値のチューニング、権限・環境変数の確認をお願いします。
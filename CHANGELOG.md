CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

未リリース (Unreleased)
------------------------
（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 全体
  - 初期リリース (バージョン 0.1.0)。パッケージメタ情報を src/kabusys/__init__.py にて設定（__version__ = "0.1.0"）。
- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機構を実装。プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で環境変数を設定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化（export KEY=val 形式、クォート文字列のエスケープ処理、インラインコメント処理を取り扱い）。
  - OS 環境変数を保護する protected オプションを導入し、.env.local の強制上書き時にも OS 環境変数を上書きしない設計。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視 / システム設定等のプロパティを提供。必須変数未設定時は ValueError を送出する _require を導入。
  - 各種設定値にバリデーションを追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- 実行スクリプト
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する旨を明示。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを終了。
    - duckdb と sqlite の接続確立と monitoring DB 初期化処理を実行。
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBroker と専用 DB (data/paper_trading.db) を使用し本番と分離。
    - 起動時に停止フラグを確認し、既にフラグがあれば起動を中止。起動後は別スレッドでエンジンを実行し停止フラグを検知するとエンジン停止を要求。
    - Execution 用の PID ファイルと停止フラグの利用を実装。
- ユーティリティ (src/kabusys/utils/process_priority.py)
  - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（set_process_priority）。Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。
  - CPU affinity 固定用の set_cpu_affinity を追加。
  - 権限不足や未サポート環境に対する安全なフォールバックとログ出力を実装。
- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック処理あり。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。unknown セクター扱いの挙動やフォールバックを明記。
  - position_sizing: 発注株数算出ロジックを追加（calc_position_sizes）。allocation_method に応じた計算 (risk_based / equal / score)、lot 単位丸め、単銘柄上限・全体上限（aggregate cap）を実装。cost_buffer を考慮した保守的なコスト見積りとスケールダウンロジックを備える。
  - package エクスポートを整備（src/kabusys/portfolio/__init__.py）。
- リサーチ・特徴量 (src/kabusys/research/*)
  - factor_research: Momentum / Volatility / Value ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily / raw_financials テーブルを参照して純粋関数として実装。
  - feature_exploration: 将来リターンの計算（calc_forward_returns）、IC (Spearman) 計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）。
- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - ニュース記事を OpenAI API（gpt-4o-mini）でスコアリングするモジュールを追加。
  - タイムウィンドウ計算 (calc_news_window)、API バッチ送信の方針、スコアのクリップ、エラー種別に応じたリトライ（指数バックオフ）方針、レスポンス検証、ai_scores テーブルへの置換更新設計をドキュメント化・実装。
  - 実装上の注意点：トークン肥大化対策（1銘柄当たりの記事数・文字数上限）、出力は厳密な JSON で取り扱う方針を採用。
  - （ソースは途中で切れている箇所があり、記事フェッチ部分の実装が続く想定）
- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成ツールを追加。SQLite（Paper Trading DB）を読んで稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算し、PASS/FAIL 判定をコンソール出力する。
  - P95 計算、日付フィルタ、DB が存在しない・テーブルが存在しない場合のフォールバックを実装。閾値は定数で管理（稼働率・成功率・送信率・P95 レイテンシ）。

Changed
- 監視・実行フロー
  - 監視・実行の起動時にプロセス優先度を "high" に設定するように変更（set_process_priority を呼び出す）。
  - 監視ループ・実行スレッドは停止フラグファイルを監視して安全に停止する挙動を導入。
- DB 初期化
  - monitoring 用テーブルの初期化（init_monitoring_db）を起動時に必ず行い、冪等に存在を保証するようにした。
- ログ・例外ハンドリング
  - ポーリングループやエンジン実行中に発生した例外はログに例外情報を出力し、次のサイクルへ継続するフェイルセーフを採用。

Fixed
- 環境変数パースの堅牢化
  - .env のクォートされた値やエスケープ、コメント処理に関する不整合を修正し、より現実の .env ファイルを正しく読み込めるよう改善。
- プラットフォーム差分の安全な扱い
  - process priority / cpu affinity 設定で権限不足・未実装 API によりクラッシュする問題を回避するため、例外捕捉と警告ログでフォールバックするように修正。

Notes / Known issues
- ai/news_nlp.py の score_news 内で記事取得フェーズ以降の実装がソースの途中で切れている（本リリース時点で該当箇所は実装継続が必要）。設計上はバッチ送信→検証→ai_scores への置換というフローを想定していますが、未完成部分の実装・テストを要します。
- position_sizing の価格欠損（price が 0.0 の場合）に関する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する予定。
- .env 自動読み込みはプロジェクトルートを検出できなかった場合にはスキップされるため、配布形態やインストール先に応じて環境変数の明示的設定が必要になる場合があります。

その他
- ドキュメント参照:
  - PortfolioConstruction.md / StrategyModel.md / Research の設計方針に基づく実装注記をソース内 docstring に記載。
- テスト:
  - 本リリースでは外部サービス呼び出し（kabu/station, OpenAI など）を行う箇所は抽象化されており、モックを使った単体テストが容易になる設計を意識しています。

お問い合わせ
- 変更点や不明点があれば、リポジトリの Issue または開発チームまでご連絡ください。
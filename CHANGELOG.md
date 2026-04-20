CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠の形式で記載しています。日付はリポジトリの現時点（2026-04-20）を基準にしています。コードから推測できる追加・改善点を日本語でまとめています。

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-20
-----------------

Added
- 全体
  - 初期バージョンを公開（__version__ = "0.1.0"）。
  - CLI / ツール群、ポートフォリオ構築、実行エンジン、監視など自動売買システムの主要コンポーネントを追加。

- 実行 / 監視スクリプト
  - run_execution.py を追加。
    - プロセス優先度を "high" に設定して実行。
    - KABUSYS_ENV が paper_trading の場合はペーパートレード用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（実運用/モックの切り替えを想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み合わせてセッションをスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを提供。
    - PID ファイルの利用（data/execution.pid 想定）。
  - run_monitoring.py を追加。
    - SystemMonitor を定期ポーリングで実行。モニタリングは環境に関わらず本番 sqlite_path を使用する設計。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグ検知で安全にループ終了。check_once() の例外はログに例外情報を残して次回ポーリングへ継続。

- 設定 / 環境変数
  - config.py に Settings クラスを実装。
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - ロード順: OS 環境変数 > .env.local > .env（.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パーサを実装（export プレフィックス、クォートされた値、インラインコメント等に対応）。
    - 必須／任意設定のアクセサリ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）、DB パス、paper_trading 用設定（PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH）や監視閾値（CPU/MEM/DISK）をプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証と便利プロパティ（is_live, is_paper, is_dev）を提供。

- 設定ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 各項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 系等）を対話的に入力可能。
    - シークレット項目は表示をマスクし、既存 .env の読み込みと Enter での再利用をサポート。
    - .env の書き出しテンプレート（コメント付き）を導入。
    - 起動時に次のステップ（validate_config の実行）を案内。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パースチェック（PyYAML があれば内容検証）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や Kill Switch の設定の警告）。
    - --strict オプションで警告を失敗扱い（exit(1)）にできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。
    - 統一的なログ設定関数 setup_logging(app_name, log_dir, level) を提供。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力。
    - 既存ハンドラの二重登録を防ぐため、設定時に既存ハンドラをクリア。
  - utils/process_priority.py を追加。
    - psutil を使い Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを提供。設定に失敗しても安全に警告を出す。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスを固定する機能を追加（利用できない環境では警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの上位選抜 select_candidates（スコア降順、タイブレークに signal_rank を使用）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に当該セクターの新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（不明なレジームは 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - risk_based: リスク割合と stop_loss を用いた株数設計。
    - equal/score: 重みを基に alloc を計算、lot_size（単元株）で丸め。
    - aggregate cap と cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング、残差に基づく lot 単位での追加配分アルゴリズムを実装。
    - 価格欠損や lot 単位の丸めに対するログ出力や安全処理を実装。

- ツール
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計して検証レポートを出力。
    - 指標: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg / max / P95）。
    - P95 の独自計算、閾値ベースの PASS/FAIL 判定（デフォルト閾値を設定）を実装。
    - CLI: --from / --to / --db オプションに対応。DB が存在しない・テーブルがない場合でもエラーを丁寧に扱う。

- 研究モジュール（未完成だが骨組みを追加）
  - research/factor_research.py にファクター計算の枠組みを追加（モメンタム・MA200・ATR・出来高等の定数と calc_momentum の初期実装を含む）。DuckDB 接続を受け、prices_daily / raw_financials を参照する設計。実装は一部で途切れている（開発途中のファイル）。

Changed
- モジュール設計
  - 設定・ログ・プロセス制御をユーティリティ化して各種起動スクリプトから統一的に利用する設計に変更。
  - .env 読み込みの優先順位や上書きポリシー（protected keys を用いた OS 環境保護）を明示的に実装。

Fixed
- 安全性 / ロバストネス
  - run_monitoring/run_execution のループで停止フラグを確認し安全に終了する仕組みを導入（強制終了ではなく優雅なシャットダウンを想定）。
  - logging_setup: ログディレクトリ作成失敗時に例外を投げずコンソールのみで継続するよう修正。
  - process_priority/set_cpu_affinity: 対応できない環境（権限不足や未対応 OS）での例外を捕捉して警告に変換。

Notes / Possible TODOs（コードから推測）
- research/factor_research.py は途中で切れており実装未完。ファクター計算ロジックの完全実装とテストが必要。
- position_sizing の price 欠損時のフォールバック（前日終値やマスタ参照）や銘柄別 lot_size のサポートは将来的な拡張候補。
- .env の書式パーサは多くのケースに対応しているが、特殊文字／エスケープの追加検証が望ましい。
- tools/paper_verification_report の閾値や判定ロジックは運用に合わせた調整が想定される。

注記
- 本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。実際の変更履歴を生成する場合は Git のコミットメッセージ／タグ情報を参照してください。
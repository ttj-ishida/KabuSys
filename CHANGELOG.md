# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
（この CHANGELOG はソースコードの内容から機能追加・設計意図を推測して作成しています。）

※ バージョン番号はパッケージの __version__ (0.1.0) に基づきます。

Unreleased
----------
- 今後の変更点をここに記載します。

0.1.0 - 2026-04-24
-----------------
Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージ情報: kabusys/__init__.py（__version__ = "0.1.0"）
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様（監視情報は本番 DB に集約）。
    - 停止フラグによる安全終了と KeyboardInterrupt のハンドリング。
- 設定・環境管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順と OS 環境変数の保護（上書き禁止）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading の設定、監視閾値、環境判定ロジック等）を提供。
    - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
  - config_setup.py（対話式ウィザード）
    - .env の初期作成・更新支援。各項目の説明、デフォルトおよびシークレットの扱いを提供。
    - .env 書き出しフォーマットを定義し、保存の確認フローを提供。
  - validate_config.py（設定検証 CLI）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェックを実装。
    - config/*.yaml の存在確認と、PyYAML が利用可能な場合は YAML パース検証を実施。
    - KABUSYS_ENV=live の際の追加警告（LINE 通知未設定や Kill Switch の自動クリア設定など）。
    - --strict オプションで警告を失敗と見なすモードを提供。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30日保持）を設定。
    - 既存ハンドラをクリーンに置換して二重設定を防止。
    - LOG_LEVEL / LOG_DIR の環境変数・引数解決とファイルハンドラ作成失敗時のフォールバックを実装。
- プロセス制御ユーティリティ
  - utils/process_priority.py
    - Windows/Linux/Mac の差分を吸収してプロセス優先度を設定する set_process_priority を実装（"high"/"normal"/"low"）。
    - psutil を利用。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity を導入し、プロセスを最初の N コアに固定する機能を提供（安全な境界チェック付き）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター毎の既存保有比率に基づく新規候補除外ロジック（unknown セクターは除外しない）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定ロジック。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮。
    - aggregate スケーリング時の残差処理（fractional remainder による追加配分）を実装。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）からデータを集計して検証レポートを出力。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し、閾値（稼働率 >= 99% 等）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）、--db オプションを提供。
- 監視データベース初期化
  - monitoring/monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等操作）。

Changed
- なし（初期リリースとしての追加が主体）。

Fixed
- なし（既知のバグ修正履歴は無し。実装中の箇所はコード内コメントで注意事項を記載）。

Deprecated
- なし。

Removed
- なし。

Security
- なし（機密情報は .env により管理する設計。config_setup において .env を Git にコミットしないよう注意喚起を出力）。

Notes / Known limitations
- research/factor_research.py はファクター計算の骨子を含むが、（ファイル末尾が途切れているなど）未完成の可能性があるため、実用化前に追加の実装・テストが必要。
- position_sizing の価格欠損時の扱い（price が 0 の場合）に関する TODO を残している。前日終値等のフォールバック処理は未実装。
- process_priority の設定には権限が必要な場合がある（警告を出して安全にスキップする設計）。
- .env パーサは単純実装であり、複雑なシェル展開や複数行値などには対応していない。

開発者向けヒント
- ローカル開発で .env を自動ロードさせたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live を設定し、validate_config を実行して警告・設定ミスを事前に確認してください。
- run_execution/run_monitoring はログ設定（logs/）やデータディレクトリへの書き込み権限が必要です。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

--- 
（ここまでがソースコードから推測して作成した CHANGELOG です。必要に応じて実際のコミット履歴・チケットに基づく追記・修正を行ってください。）
Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。リリースはパッケージ内の __version__ を参照して v0.1.0 とし、日付は現在日付 (2026-04-21) を使用しています。必要に応じて日付や版番号を変更してください。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog — https://keepachangelog.com/ (日本語訳に準拠)

未リリース
---------

- （次回以降に記載）

v0.1.0 - 2026-04-21
-------------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトルート/data/stop_requested.flag により行う。
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用して DB に接続する。
    - 例外は catch してログ出力し、次のポーリングまで待機する堅牢化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、専用の Paper Trading 用 SQLite（既定: data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
    - Engine は別スレッドで run_session を実行。停止フラグでの安全停止をサポート。
    - PID ファイル管理（data/execution.pid）と停止フラグチェックを実装。

- 設定まわり
  - config.py: 環境変数/設定管理クラス Settings を追加。
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 必須値取得用の _require と各種設定プロパティ（DB パス、KABU API、LINE、監視閾値、環境判定等）を提供。
    - PAPER_FILL_MODE の厳密検証（instant/partial/never/reject）を追加。
    - env/log_level のバリデーションを追加（許容値に違反すると ValueError）。

- 設定支援ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 秘匿項目は表示時にマスクし、既存 .env を読み込んで再利用可能。
    - 書き込みフォーマットと注意書きを含む .env を生成。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース検証（PyYAML が存在する場合）。
    - --strict オプションで警告も失敗（exit code 1）に昇格可能。
    - 本番（KABUSYS_ENV=live）時のガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の危険表示）を追加。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力） と 日次ローテーション (TimedRotatingFileHandler) を root ロガーへ設定。
    - LOG_LEVEL と LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/macOS 等）の差分を吸収する実装。
    - set_process_priority(level) で "high"/"normal"/"low" をサポート（psutil 使用）。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定できる（アクセス権等で失敗する場合は警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank を用いたタイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分を実装。全銘柄スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用可能現金に対する aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、スケールダウン後の残差分配（再現性のある順序）を実装。
    - 価格欠損や 0 値はスキップして安全に動作。

- 監視・検証ツール
  - monitoring/monitoring_db の初期化呼び出しを run_monitoring / run_execution の起動時に追加し、監視テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を行う。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。コマンドライン引数 --from/--to/--db をサポート。
    - P95 計算、各種クエリ関数（system_status, trade_logs, risk_logs）を実装。
    - 基準値（閾値）を定義: 稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

- パッケージ初版情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- 初版リリース。既存コンポーネントの統合と起動フローの整備を行い、各種ユーティリティを追加。

Fixed
- （このリリース内での個別バグ修正は明示的には無し、各モジュールはエラー耐性（例: DB パス未作成時の警告・例外捕捉）を強化）

Notes / Implementation details
- .env 自動ロードはプロジェクトルートが判定できない場合はスキップされるため、配布後の環境でも予期せぬ上書きを防止。
- run_monitoring はモニタリングデータ用に常に Settings.sqlite_path（本番用）を使用する設計になっている点に注意。実行環境に応じた DB を用いたい場合は設定側で SQLITE_PATH を変更するか run_monitoring を修正する。
- logging_setup は stdout を使う設計（stderr ではなく stdout）。これは cron 等からのログリダイレクト運用を考慮した意図的な選択。
- process_priority や CPU affinity の設定は権限がない環境では警告に留めるため、デプロイ先の権限や OS によっては効果がない場合がある。
- portfolio や research の関数は純粋関数（副作用なし）として設計されており、ユニットテストで容易に検証できる想定。

Security
- 秘匿情報（トークンやパスワード）は .env に保存する前にマスク表示する等の UX を配慮（config_setup の対話表示）。
- .env は Git にコミットしないよう生成時に注意書きを含めています。

Acknowledgements
- 初版機能群（起動スクリプト、設定管理、ログ/プロセスユーティリティ、ポートフォリオ構築、検証ツール）を取りまとめて公開しました。今後はテスト、文書化（API/設計ドキュメント）、strategy/research の追加実装、運用向けのオプション強化を予定しています。

--- 

必要であれば、各変更項目をより細かいコミット単位やファイル差分ベースで分割して記載します。どの程度の粒度での CHANGELOG を望むか教えてください。
CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project follows "Keep a Changelog" の形式と、セマンティック バージョニングを使用します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性あり/注意点）
- Fixed: バグ修正
- Removed: 削除事項
- Security: セキュリティ関連

※ 本ログはソースコードの内容から推測して作成しています（実装上の意図に基づく要約）。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を導入。
- 実行用エントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。スレッドでエンジンを実行し、stop フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離するロジックを追加。
    - BrokerClientFactory を用いたブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - RiskConfig の初期値（例: max_position_pct=0.20, max_utilization=0.80 など）を設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔変更可能（デフォルト 60 秒）。停止フラグ検出でループ終了。
    - 監視用 DB の初期化を実施（monitoring は環境にかかわらず production sqlite_path を使用する旨を明記）。
- 設定管理と初期化支援ツールを追加。
  - config.py
    - .env ファイルの自動読み込みロジック（プロジェクトルートの検出、.env/.env.local の読み込み）を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - Settings クラスに環境変数プロパティを定義（J-Quants, kabu API, DB パス, Paper Trading 設定, 監視しきい値, ログレベル等）。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject" のみ許可）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。シークレット項目はマスク表示、既存 .env の読み取り/再利用に対応。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を実装。必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリ確認、YAML ファイル存在/パース検証（PyYAML が無い場合はスキップ）などを行う。--strict により警告を FAIL 扱いにできる。
- ロギングとプロセス制御ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する統一ロギングセットアップを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）を設定する関数を追加。CPU affinity を設定する set_cpu_affinity も提供。権限不足や未対応 OS の場合はログ警告でスキップする安全策を実装。
- ポートフォリオ構成・注文サイズ計算モジュールを追加（純粋関数群）。
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（合計スコアが 0 の場合は等金額へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（"bull":1.0, "neutral":0.7, "bear":0.3、未知値は警告して 1.0 でフォールバック）を実装。既存ポジション・当日売却予定の除外等を考慮。
  - portfolio/position_sizing.py
    - allocation_method に応じた発注株数計算 calc_position_sizes を実装。risk_based / equal / score に対応。単元株（lot_size）で丸め、ポートフォリオ上限・銘柄上限・コストバッファ（cost_buffer）を考慮した aggregate cap スケーリングロジックを含む。
- Paper Trading 向け検証レポート生成ツールを追加。
  - tools/paper_verification_report.py
    - paper_trading の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計するレポートを生成。
    - Pass/Fail 基準（稼働率 >= 99%, 成立率 >=90%, 送信率 >=95%, P95 latency <=200ms）を定義し、判定を出力。
- データ解析用スケルトンを追加。
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨組み（Momentum / Value / Volatility / Liquidity）を追加。関数や定数（期間設定、スキャン範囲など）の定義を含む（calc_momentum の実装は途中まで含まれる）。

Changed
- 監視/実行スクリプトの挙動について仕様を明確化。
  - run_monitoring.py: MONITOR_POLL_INTERVAL の不正値時に警告を出しデフォルト値 60 秒へフォールバックする堅牢化を行った。
  - run_monitoring.py / run_execution.py: 起動時に set_process_priority("high") を呼び出して優先度を引き上げる実装を追加（処理を開始する最初のステップとして）。
  - run_execution.py: 起動前に停止フラグが既に立っている場合は起動せず終了するガードを実装。
- config.py の自動 .env ロード順と保護挙動を明確化。
  - OS 環境変数を保護しつつ .env/.env.local をロードするロジック（.env は既存変数を上書きせず、.env.local は上書きするが OS 環境変数は保護する）が実装された。
- logging_setup.py: stdout を StreamHandler に使用（stderr ではない点を明示）。既存ハンドラは flush/close 後に削除して二重設定を防止する。

Fixed
- 設定ファイル読み書きに関する細かい扱いを改善。
  - config_setup.py: 既存 .env の読み込み/マスク表示、対話入力のキャンセル時の振る舞い（中断時のメッセージと保存キャンセル）を扱う。
- Paper Verification レポートの集計でデータ欠如時に例外を吸収し、N/A 表示やデフォルト値で堅牢に振る舞うようにした（sqlite OperationalError を捕捉してフォールバック）。

Removed
- （なし）

Security
- 環境変数ファイル (.env) の取り扱いに関する注意を追加（config_setup.py に .env を Git にコミットしない旨の警告を記載）。

Notes / 注意事項
- 設定の自動読み込みはプロジェクトルート検出に依存する（.git か pyproject.toml）。配布後や異なる展開方法では自動検出されない場合がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動ロードを無効化してください。
- run_monitoring は「監視 DB に常に本番 sqlite_path を使用する」仕様となっているため、paper_trading 環境でも監視テーブルは本番用 DB を参照する点に注意してください（run_execution は paper_trading 時に専用 DB を使用する）。
- process_priority の変更は権限問題で失敗することがあります。その場合は警告を出して処理を継続します。
- portfolio/position_sizing の一部ロジックは価格欠損（0.0）の場合に過少見積りとなる可能性があり、将来的なフォールバック価格取得の TODO が残されています。

今後の改善案（推奨）
- research/factor_research のファクター計算を完成させ、DuckDB クエリ最適化とユニットテストを追加する。
- portfolio モジュールに対する網羅的なユニットテスト（特にスケーリングと端数処理）を追加する。
- run_execution / run_monitoring の統合的なシグナルハンドリング（デーモン化、サービス化）を検討する。
- ログの構造化（JSON 出力等）やメトリクス収集（Prometheus 等）を検討する。

---  
（この CHANGELOG はソースコードから推測して作成した要約です。実際のリリースノート作成時は追加の設計意図や変更履歴（コミットログ等）を参照して補完してください。）
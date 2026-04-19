Keeps a Changelog 形式に準拠した CHANGELOG.md（日本語）を下記に作成しました。本リリースはソースコードから推測できる機能追加・設計意図を基に記述しています。

CHANGELOG.md
============
すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" を参照しています。

[Unreleased]

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージ初期実装（バージョン 0.1.0）
  - src/kabusys/__init__.py によるパッケージ定義とバージョン設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV により paper_trading（モックブローカ）と本番を切替可能。
    - Paper Trading 時は専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた起動/停止制御。
    - スレッドでエンジンを実行し、停止フラグ検出で安全に停止する制御ループ。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等のコンポーネント組み立てを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）をコード内で指定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知、例外発生時のロギング継続、KeyboardInterrupt による終了処理を実装。
    - SQLite / DuckDB 接続の初期化とクローズ処理を実装。

- 設定 / 環境変数管理
  - config.py
    - Settings クラスを提供。各種環境変数（J-Quants、kabu API、LINE、DB パス、監視閾値、実行環境など）をプロパティとして取得。
    - KABUSYS_ENV の検証（development / paper_trading / live）や LOG_LEVEL の検証を実装。
    - paper_fill_mode の妥当値チェック（instant/partial/never/reject）。
    - 環境変数の自動ロード機能:
      - プロジェクトルート (.git または pyproject.toml) を探索し、.env（優先度低）と .env.local（優先度高）を読み込む。
      - OS 環境変数を保護する仕組みを導入。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - settings = Settings() のグローバル提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI。
    - J-Quants トークン、kabu API パスワード、DBパス、ログレベル、KABUSYS_ENV 等の入力を補助。
    - 既存 .env の読み込みと Enter による既存値再利用、シークレット項目のマスク表示、保存前の確認を実装。
    - .env ファイルの書式テンプレートを生成（Git にコミットしないよう注記あり）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を確認する CLI。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）の未設定チェック。
    - KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML が無ければ YAML 検証はスキップして警告）。
    - --strict オプションで警告をエラー扱いにできる。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。

  - .env パーサの改良
    - export KEY=val 形式、引用符（シングル/ダブル）中のバックスラッシュエスケープ、行内コメントの扱いなどに対応した堅牢なパーサ実装を提供（_parse_env_line, _load_env_file）。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。ルートロガーを初期化して StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR 環境変数、引数によるオーバーライドに対応。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化して stderr に警告。
    - コンソールは stdout を使用（cron/スケジューラでのリダイレクト対策）。

- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity(cpu_count) により先頭 N コアへの固定をサポート（権限不足や未対応 OS は警告してスキップ）。
    - psutil を利用。例外はログに警告として処理。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で並べ上位 N を返す（タイブレークに signal_rank）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で正規化。スコアが全て 0 の場合は等分配にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別エクスポージャを計算し、既存保有が上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未登録レジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 重み／候補／ポートフォリオ値／現金等から発注株数（単元丸め）を計算。
      - risk_based / equal / score の allocation_method をサポート。
      - リスクベースでは risk_pct, stop_loss_pct を利用して株数を算出。
      - 1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、単元（lot_size）に基づく丸め処理を実装。
      - aggregate cap（全体コストが available_cash を超える場合）のスケーリングと、小数端数に対する再配分ロジックを実装。
      - cost_buffer による手数料/スリッページの保守的見積りに対応。

  - portfolio/__init__.py で主要関数をエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートを生成する CLI。
    - 取得指標:
      - system_status から稼働率・ポーリング数
      - trade_logs から Created / Filled / Sent カウント、成功率・送信率、レイテンシ（avg/max/P95）
      - risk_logs からリスク却下数
    - P95 計算、期間フィルタ（--from / --to）、閾値判定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency <= 200ms）に基づく PASS/FAIL 判定を出力。
    - DB が欠けるテーブルや欠損値に対しては N/A を適切に表示。

- リサーチ（ファクター計算）基盤（部分実装）
  - research/factor_research.py
    - ファクター（Momentum/Value/Volatility/Liquidity）計算方針と定義を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。
    - モメンタム計算 calc_momentum の実装が開始されている（ファイル末尾で途中に見えるため今後拡張予定）。

Security
- 環境変数 .env ファイル生成時に「.env を絶対に Git にコミットしないこと」を明記。

Notes
- DuckDB と SQLite の併用設計:
  - DuckDB は分析（prices_daily 等）用途、SQLite は監視・注文履歴用途で使い分けられている。
- 停止制御:
  - 複数スクリプトで共通の stop flag（data/stop_requested.flag）を使った安全停止設計を採用。
- エラーハンドリング:
  - run_monitoring は monitor.check_once() の例外を捕捉してループを継続。run_execution はスレッド監視とタイムアウト join を実装して安全終了を図る。

Deprecated
- なし

Removed
- なし

Fixed
- なし（初回リリースに相当するため履歴は「Added」に集中）

---

補足:
- 本 CHANGELOG は与えられたソースツリーの内容から推測して記載しています。実際のリリースノートではコミット履歴や CHANGELOG ポリシーに従い、より細かな著者・チケット番号・破壊的変更の注意などを付記してください。
# Keep a Changelog — CHANGELOG.md（抜粋）

すべての変更は SemVer に従います。  
このファイルは変更点を人間に読みやすく記録することを目的としています。

全体方針:
- 追加: 新機能、CLI、モジュール、ユーティリティなど
- 変更: 既存機能の挙動変更（互換性に注意）
- 修正: バグ修正や堅牢性向上
- 削除/破壊的変更: 後方互換性を壊す変更（明示）

---------------------------------------------------------------------
## [0.1.0] - 2026-04-21

### 追加
- 基本パッケージ初期リリース
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 実行系 / 監視系起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番DBと完全に分離する仕組みを導入。
    - ブローカークライアント生成（BrokerClientFactory）や OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド起動・停止制御を実装。
    - data/execution.pid に PID を記録する仕組みを想定（pid_file を渡す）。
    - data/stop_requested.flag を用いた外部停止フラグ検出に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB（sqlite）は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）や KeyboardInterrupt による安全終了処理を実装。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを実装。
    - .env のパーサはシングル/ダブルクォート、export プレフィックス、インラインコメント、エスケープに対応。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / 監視閾値 / KABUSYS_ENV / LOG_LEVEL など）をプロパティで参照可能に。
    - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- 設定検証・ウィザード CLI
  - validate_config.py
    - .env および config/*.yaml の不足や不備を起動前に検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、YAML パース検査（PyYAML がない場合は警告）、本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）等を実施。
    - `--strict` オプションで警告を FAIL として扱える。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 秘密値はマスク表示、選択肢／デフォルト提示、キャンセル時の挙動、保存確認などを実装。
    - 保存時にテンプレートヘッダ付きの .env を生成。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、`--db` または PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート / 候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights; スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有からセクター比率を算出し上限超過セクターの新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）、単元株丸め、1 銘柄上限や aggregate cap の実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り、available_cash に合わせたスケーリング、端数処理（lot_size 単位での再配分）を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL, LOG_DIR, app_name, level 引数等で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
    - 標準的な優先度ラベル（high/normal/low）をサポートし、権限不足や未対応 OS の場合は警告ログでスキップする安全設計。
- research/factor_research.py
  - ファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高等を計画）。DuckDB 接続を受ける設計。モメンタム計算関数の雛形を含む（実装継続想定）。

### 変更
- ロギングの標準出力先を stdout に統一
  - cron/Task Scheduler など外部実行環境で stdout/stderr のリダイレクト運用を想定して stdout を使用する設計に変更。
- .env 自動ロードの挙動を明文化
  - プロジェクトルートの検出ロジックを __file__ ベースで実行するため、CWD に依存しない自動ロードを実現。
  - OS 環境変数は保護され、.env.local による上書きは OS 環境変数を上書きしない（protected set）。

### 修正 / 堅牢性向上
- 環境変数のパース強化
  - export 接頭辞、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応し、.env の互換性を強化。
- MONITOR_POLL_INTERVAL の入力検証
  - 0 以下や非整数が指定された場合は警告を出し、デフォルト（60 秒）へフォールバックするようにした（time.sleep に無効値を渡さないよう保護）。
- DB 初期化の冪等化
  - init_monitoring_db() を呼ぶことで監視テーブルの存在を保証（複数回呼んでも安全）。
- 各種エラー時のログ出力改善
  - monitor.check_once() 等、ポーリングループ内の予期しない例外をキャッチして例外ログを出し、次のポーリングへ継続する仕様に変更（監視の持続性向上）。
- calc_score_weights のフォールバック
  - 全銘柄スコアが 0 の場合は警告を出し、等金額配分へフォールバックするようにした。
- position_sizing のスケーリングロジックの安定化
  - lot_size 単位での端数処理、残余キャッシュを用いた追加配分アルゴリズムを実装し deterministic（再現性）を確保。

### 既知の制限（注意事項）
- research/factor_research.py はファクター計算の骨子を含むが、いくつかの関数は未完（以降の実装が必要）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存する。環境により追加インストールが必要。
- .env に秘密情報を含める設計のため、.env をリポジトリにコミットしない運用ルールを強く推奨（config_setup.py のヘッダにも注意書きを付加）。

---------------------------------------------------------------------
今後の予定メモ（未実装 / 予定）
- research モジュールの完全実装（Momentum / Value / Volatility / Liquidity の各計算実装完了）
- 統合テスト・CI での自動検証追加
- 銘柄別の lot_size 対応（stocks マスタ導入）
- ExecutionEngine / Monitoring の振る舞いをさらに細分化した設定化（ポーリング間隔や優先度の動的制御等）

---------------------------------------------------------------------
脚注:
- 各 CLI は python -m kabusys.<module> で実行可能な設計になっています（例: python -m kabusys.config_setup）。
- 環境変数のデフォルトやパスは Settings クラスのプロパティ定義を参照してください（デフォルト例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
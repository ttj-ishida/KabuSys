CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルはコードベースから推測して作成した初回リリース向けの要約です。

Unreleased
---------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション骨格を追加
  - パッケージ情報:
    - kabusys.__version__ = 0.1.0

- 起動スクリプト / 実行フロー
  - run_execution.py:
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - ブローカークライアントの抽象化（BrokerClientFactory）により実稼働 / モックを切り替え可能。
    - ExecutionEngine をデーモンスレッドで実行し、 data/stop_requested.flag を検知して安全に停止可能。
    - 実行時に process priority を "high" に設定するユーティリティを呼び出す。
    - PID ファイル (data/execution.pid) をサポート。

  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）。
    - 監視は環境に関わらず設定された sqlite_path（デフォルト: data/monitoring.db）を使用する点に注意。
    - data/stop_requested.flag を検知してループを終了。

- 環境設定 / 検証ツール
  - config.py:
    - 環境変数の集中管理クラス Settings を実装。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を検出して .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行パースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等）。
    - 各種設定プロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - LINE チャネル設定（任意）
      - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のパス解決
      - PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）
      - 各種閾値（CPU/MEMORY/DISK 等）
      - KABUSYS_ENV のバリデーション（development, paper_trading, live）
      - LOG_LEVEL のバリデーション

  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新できる CLI。
    - 秘匿項目のマスク表示、選択肢サポート、既存値の読み込み・再利用、最終確認後に .env を保存。

  - validate_config.py:
    - 起動前チェック CLI。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML 利用可能時）などを検査。
    - --strict オプションで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定や KILL フラグ自動クリア設定の警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank 小さい方を優先）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等配分にフォールバック（WARNING）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別上限 (max_sector_pct) を考慮して新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバック（WARNING）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）を実装。
    - スケーリング時に残余キャッシュに基づく再配分ロジックを備える（再現性のためソート安定化）。
    - cost_buffer による手数料/スリッページの保守的見積を考慮。

- ユーティリティ
  - utils.logging_setup:
    - 全起動スクリプトで共通利用できるログ設定ユーティリティ。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定し、logs/<app_name>.log に出力（デフォルト logs/、30 日保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。

  - utils.process_priority:
    - psutil によって Windows / POSIX（Linux/Mac/FreeBSD）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティ。
    - CPU affinity 設定ヘルパー（最初の N コアに固定）を提供。
    - 権限不足や未対応環境では警告を出してスキップ。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード用の検証レポート生成 CLI。
    - 指標: 稼働率(uptime_pct), 注文成功率(fill_rate), 送信率(send_rate), P95 レイテンシ 等。
    - デフォルト閾値を定義し、PASS/FAIL 判定を行う（閾値: uptime>=99%, fill>=90%, send>=95%, P95<=200ms）。
    - --from/--to/--db オプションをサポート。

- 研究用モジュール（research）
  - research.factor_research:
    - DuckDB 接続を受けて各種ファクター（Momentum, Value, Volatility, Liquidity）を計算する枠組みを実装。
    - 設計方針や定数を含む初期実装。注: 実装の一部（calc_momentum 以降）がコードベースの断片で途中までの形で含まれているため、今後の完成が必要。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Deprecated
- （初回リリースのため履歴なし）

Removed
- （初回リリースのため履歴なし）

Security
- 環境変数やシークレットは .env を推奨し、.env を誤ってコミットしないよう config_setup のヘッダで注意喚起。

Notes / Usage
- 起動例:
  - 監視ループ: python -m kabusys.run_monitoring
  - エンジン起動: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

- 重要な環境変数（抜粋）:
  - KABUSYS_ENV: development | paper_trading | live（必須・検証あり）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動を制御）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading モード用）
  - SQLITE_PATH, DUCKDB_PATH: 各種 DB パス（デフォルト data/monitoring.db, data/kabusys.duckdb）

- ファイルベースの制御:
  - 停止: data/stop_requested.flag を作成すると監視／実行が安全に終了します。
  - PID: data/execution.pid（ExecutionEngine が PID を管理）。

Known limitations / TODO
- research.factor_research の一部が未完（今後ファクター計算ロジックの完成が必要）。
- position_sizing の lot_size は全銘柄共通で仮定。将来的に銘柄別 lot_map のサポートを想定する旨の TODO を含む。
- apply_sector_cap は price_map に欠損値(0.0)があると過少評価される可能性があり、フォールバック価格の導入を検討中。

Copyright & License
- コードコメントや設計に基づき CHANGELOG を作成しました。実際のライセンスはリポジトリに従ってください。
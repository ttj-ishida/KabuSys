Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測できる追加・変更点をまとめています。

CHANGELOG.md
-------------

すべての変更は semver 準拠で記載しています。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（今後のリリースで記載）

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - 初期公開リリースを追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト / デーモン
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db デフォルト）を使用して本番データと分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - ExecutionEngine をスレッドで起動し、data/execution.pid を PID 管理に利用。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み立て、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告のうえデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV に依らず production の sqlite_path を使用する挙動を明示（監視データは本番 DB を参照）。
    - 停止フラグファイル検知でループを終了。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位は OS 環境変数 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの考慮）。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / kill flag 関連 / CPU/MEM/DISK 閾値 / KABUSYS_ENV / LOG_LEVEL 等）。値検証を実施（有効な列挙値チェックなど）。
- 設定ユーティリティ / CLI
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガードなど。
    - --strict フラグで警告を FAIL 扱いにできる。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 多数の設定項目を対話的に入力・保存する機能（.env を生成）。シークレット項目はマスク表示。デフォルト値や説明を表示。
- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラはクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収して優先度設定を実行。AccessDenied 等の例外をハンドルしてフォールバック。
    - set_cpu_affinity によりプロセスを最初の N コアへピン留め可能。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順ソート、signal_rank によるタイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有比率に基づく候補除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" マッピング、未知レジームは警告して 1.0 にフォールバック）
  - 株数決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート、lot_size による丸め、per-stock 上限と aggregate cap（available_cash）を考慮、cost_buffer による保守的見積り、スケールダウンと残差に対する lot 単位の追加配分ロジックを実装）
  - モジュールエクスポート（src/kabusys/portfolio/__init__.py）
- 研究・ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、ATR（20日）などの定数・方針を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。（calc_momentum の実装が含まれているが、ファイル末尾が未完の可能性あり。）
- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を算出して判定（閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB が存在しない場合のエラーメッセージ、SQL の OperationalError に対する耐性を実装。

Changed
- DB と分析
  - DuckDB 接続を各コンポーネントで利用（duckdb_path の設定）。run_monitoring/run_execution で duckdb を接続して各種処理（分析/ログ保存）に利用可能にした。
- ロギング
  - StreamHandler を stdout に向ける（stderr ではなく）。cron/Task Scheduler からの起動時に stdout/stderr を一本化して扱いやすくするため。
- .env 読み込み優先度
  - OS 環境変数を保護するため .env 読み込み時に protected（既存 os.environ のキー）を考慮。`.env.local` は `.env` を上書きする。

Fixed
- 設定パースの堅牢化
  - _parse_env_line の quoted value 処理にエスケープ対応を追加し、クォート内部の # をコメント扱いしないように修正。
- ログ初期化時のハンドラ二重登録回避
  - setup_logging で既存ハンドラを明示的に flush/close/削除してから再設定するように変更。複数回 setup_logging を呼んでも重複出力しない。
- 優先度設定の例外ハンドリング
  - set_process_priority/set_cpu_affinity が権限不足や未実装 API によって失敗した際に警告ログを出して処理を継続するように改善。

Security
- .env の取り扱いに関する注意喚起を config_setup の生成ヘッダに明記（.env を絶対に Git にコミットしないこと）。

Notes / Breaking changes
- 監視（run_monitoring）は「環境にかかわらず」production 用 sqlite_path を使用する挙動があるため、テストやローカル実行時に監視データを分離したい場合は sqlite_path を明示的に設定してください。
- config.Settings の各プロパティは起動時に ValueError を送出することがあるため、CI/環境構築時には必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）や列挙値（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を正しく設定してください。

参照ファイル
- 起動/管理: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/*.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- 研究: src/kabusys/research/factor_research.py
- ツール: src/kabusys/tools/paper_verification_report.py

---

補足:
- 本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のコミット履歴や意図とは差異がある可能性があります。必要であれば差分やコミットメッセージを提示いただければ、細かい変更点（責務分離、リファクタ、バグ修正の詳細など）をより正確に反映できます。
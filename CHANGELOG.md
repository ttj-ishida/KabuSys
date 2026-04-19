# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。（https://keepachangelog.com/ja/）

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコア機能と運用ユーティリティを追加。

### Added
- 全体
  - パッケージ初版を追加。バージョンは `__version__ = "0.1.0"`。
  - DuckDB / SQLite によるデータ永続化や分析処理の統合（デフォルトパス: `data/kabusys.duckdb`, `data/monitoring.db`）。
  - 環境変数ベースの設定読み込み・管理機能（`kabusys.config.Settings`）。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出に基づく）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 必須値取得ヘルパー `_require`、各種環境変数のデフォルトや検証（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` など）。
- 実行用スクリプト / デーモン
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、本番 DB と分離して `data/paper_trading.db` を利用する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority` を使用）。
    - 停止管理用フラグファイル（`data/stop_requested.flag`）と PID ファイルサポート。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
    - 監視(Diagnostics)は環境に関わらず本番の `sqlite_path` を使用して監視データを記録。
    - 停止フラグ検知でループを終了。
- 設定補助 / 検証ツール
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成 / 更新する CLI を追加。シークレット扱い、選択肢、デフォルト値表示をサポート。
    - `.env` ファイルの読み書きロジックを実装（既存値の読み込み、mask 表示、保存確認）。
  - `validate_config.py`
    - 起動前に .env と `config/*.yaml` を検証する CLI を追加。
    - 必須環境変数未設定、プレースホルダ値、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML がある場合）などを実行。`--strict` で警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`
    - シグナルの候補選定（スコア降順、タイブレークルール）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（スコア合計が 0 のとき等配にフォールバック）。
  - `portfolio.risk_adjustment`
    - セクター集中制限を実装する `apply_sector_cap`（当日売却予定の銘柄除外や "unknown" セクターは無視する挙動）。
    - マーケットレジームに基づく投下資金乗数 `calc_regime_multiplier`（`bull/neutral/bear` -> `1.0/0.7/0.3`、未定義レジームはフォールバックと警告）。
  - `portfolio.position_sizing`
    - 各銘柄の発注株数を計算する `calc_position_sizes` を実装。
    - アロケーション方式: `risk_based`, `equal`, `score` をサポート。
    - 単元株（lot_size）丸め、銘柄ごとの上限（max_position_pct）、全体の投下上限（max_utilization）を考慮。
    - cost_buffer を用いた保守的なコスト見積り、aggregate cap 超過時のスケーリング（端数配分ロジックを含む）。
- ユーティリティ
  - `utils.logging_setup.setup_logging`
    - 統一的なロギング初期化。コンソール出力は stdout に統一（cron 等でのリダイレクトを想定）。
    - 日次ローテートファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を回避。
  - `utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定する `set_process_priority`。
    - CPU affinity を設定する `set_cpu_affinity`（利用可能コア数より大きい数が指定された場合の安全弁、権限不足時の警告対応）。
- モニタリング / DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を呼ぶことで監視テーブルの冪等な初期化を行う（run_monitoring, run_execution で使用）。
- ツール
  - `tools.paper_verification_report.py`
    - Paper Trading の検証レポート生成ツールを追加（期間指定オプション、DB パス指定オプションをサポート）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を判定。閾値はソース内定義（例: 稼働率 >= 99%）。
- リサーチ（未完／スケルトン）
  - `research.factor_research.py` の骨子を追加（Momentum / Value / Volatility / Liquidity の設計方針と定数が含まれる）。DuckDB 接続を受ける設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境ファイルパーサーの堅牢化（`kabusys.config._parse_env_line`）
  - `export KEY=val` 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート内は無視）、クォートなしのコメント解釈ルールなどに対応。
  - `.env` の読み込み失敗時には警告を出しつつ起動継続する実装。
- ロギングハンドラの多重登録防止（既存ハンドラを flush/close してから削除）。
- `MONITOR_POLL_INTERVAL` の不正値処理：0 以下や非整数文字列はログで警告してデフォルトにフォールバック。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記:
- 多くのコンポーネントは「防御的」に実装されており、権限不足やファイルシステムエラー、外部ライブラリ未インストール時でも安全にフォールバックして運用を継続する設計になっています（ログ出力に関するフォールバック、env 読み込みの保護、プロセス優先度設定の例外処理など）。
- 各 CLI（config_setup / validate_config / tools.paper_verification_report / run_*）は単体で実行可能で、運用時の設定検証・初期化・監視・検証に役立ちます。

今後の予定（参考）
- research.factor_research の完全実装（SQL + Python によるファクター計算）。
- Strategy / Execution の詳細なユニット（Strategy モジュール、ExecutionEngine の詳細なテスト等）。
- 単体テスト・統合テストの追加と CI 設定。
CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

なし

0.1.0 - 2026-04-22
------------------

初回リリース（推定）。以下の主要機能・ユーティリティを追加しました。

Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定し、ExecutionEngine を別スレッドで起動・監視する。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と完全分離された専用 SQLite（デフォルト: data/paper_trading.db）を使用する想定（MockBrokerClient の利用は BrokerClientFactory に委譲）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグでループを終了、例外はログ出力して次ポーリングへフォールバック。

- 環境設定 / 検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。多くの設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）に対応。
    - シークレット項目は表示をマスクして入力を受け付ける。
  - validate_config.py
    - .env と config/*.yaml の起動前検証用 CLI を追加。--strict オプションで警告も失敗扱いにできる。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を実行、live 環境向けの追加警告などを実装。

- 設定読み込み / 管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml で検出）。読み込み順は OS 環境変数 > .env.local > .env。
    - export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱いなどを考慮したパーサ実装。
    - 自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスで各種設定値をラップ（検証付き）。例: PAPER_FILL_MODE の有効値検査、KABUSYS_ENV / LOG_LEVEL の検証、duckdb/sqlite/paper_sqlite 等の Path 解決、しきい値系の float プロパティ等。
    - settings = Settings() をモジュールレベルで提供。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - setup_logging(): stdout への StreamHandler と日次ローテートされた TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30日保持）をルートロガーに設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続する。
    - ログレベル解決順: 引数 level > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX の違いを吸収してカレントプロセスの優先度を設定するユーティリティを追加（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count): 指定数のコアにプロセスを固定するユーティリティを追加（権限不足や未対応環境では警告を出してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に応じて候補銘柄を除外するロジック（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに応じた乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）、未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式 ("risk_based", "equal", "score") に対応した株数決定ロジックを追加。単元株丸め（lot_size）・1 銘柄上限・aggregate キャップのスケーリング（端数処理を考慮）を実装。
    - cost_buffer を用いた保守的なコスト見積り、available_cash 超過時のスケールダウンロジックを実装。
    - TODO / 将来拡張: 銘柄別 lot_size サポートの注記あり。

- 監視 / モニタリング関連
  - monitoring 初期化へのフック（init_monitoring_db を利用して冪等に監視用テーブルを担保）。
  - SystemMonitor を用いた単回チェック（monitor.check_once() 呼び出し）をループ化。

- Paper trading 向けの検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH を使用）から統計（稼働率・注文成功率・送信率・P95 レイテンシ等）を算出してレポート出力する CLI を追加。
    - P95 計算、期間フィルタ（--from / --to）、閾値比較による PASS/FAIL 判定を実装（デフォルト閾値: 稼働率 99.0% 等）。
    - DB が存在しない場合やテーブルが欠けている場合はエラーや N/A 表示で寛容に扱う（例外は捕捉してデフォルト値で続行）。

- データ分析 / リサーチ
  - research/factor_research.py
    - ファクター計算の枠組み（Momentum, Value, Volatility, Liquidity）の開始実装。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算（calc_momentum）のための定数やドキュメントを追加。
    - 注意: calc_momentum の実装が途中で切れている箇所（ソース末尾で未完）あり。後続実装が必要。

Changed
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を追加。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （目立ったセキュリティ修正は無し。ただし .env を Git にコミットしない旨を config_setup の生成ヘッダに明記）

Notes / Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で終わっており、実際のファクター出力を得るには追加実装が必要です。
- portfolio/risk_adjustment.apply_sector_cap にて price が欠損（0.0）の場合にエクスポージャーが過小評価され、適切にブロックされない可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバック価格導入が検討されています。
- position_sizing は現時点で全銘柄共通の lot_size を想定。将来的には銘柄別 lot_map を受け取る拡張が予定されています。
- process_priority / set_cpu_affinity やログディレクトリ作成は権限不足などで失敗することがあり、その場合は警告を出して処理をスキップする挙動です。

以上。コードベースから推測した主要な変更・追加点をまとめました。必要であれば、各モジュールごとのより詳細な変更説明やリリースノートの分割（例: Monitoring / Execution / Portfolio / Tools）を作成します。
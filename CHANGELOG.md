# Changelog

すべての notable な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

通常のセクション: Added, Changed, Fixed, Deprecated, Removed, Security。

## [0.1.0] - 2026-04-18
初回リリース。本リリースで追加された主要機能と変更点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。これにより CWD に依存せず .env 自動ロードを行えるように。

- 環境 / 設定管理
  - Settings クラスを実装し、環境変数から各種設定を取得可能に。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境フラグ等をプロパティとして提供。
    - KABUSYS_ENV（development / paper_trading / live）の検証を実装。
    - LOG_LEVEL の検証を実装。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）をサポート。
  - .env ファイル自動ロード機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースを強化：
    - export プレフィックス対応、クォート（' / "）内のエスケープ処理、行内コメント処理などをサポート。

- CLI / ツール
  - config_setup.py：対話式ウィザードにより .env を作成 / 更新する機能を追加。
    - 典型的な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話式に入力可能。
    - シークレット項目はマスク表示し、保存前に確認プロンプトを表示。
  - validate_config.py：起動前設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML が利用可能な場合）など。
    - --strict オプションで警告を失敗扱いにできる。
  - tools/paper_verification_report.py：Paper Trading 用の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を行う。
    - デフォルトしきい値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 <= 200 ms。
    - --from / --to / --db オプションをサポート。
    - PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB を参照。

- 実行 / 監視
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（settings.paper_sqlite_path）を使用して本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory により適切なブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) を監視し、フラグ検知で安全に停止。
    - PID ファイル（data/execution.pid 相当）を利用。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを永続化（monitoring 用 DB 初期化を実行）。
    - 停止フラグでループを終了、KeyboardInterrupt に対応。
    - プロセス優先度を "high" に設定して起動。

- ポートフォリオ構築（pure functions, DB 参照なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア順にソートし上位 N を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights を実装（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を制限するフィルタ実装（既存ポジションのセクターエクスポージャを計算し上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づいて発注株数を算出。
    - 単元株丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap（available_cash）や cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングを実装。
    - risk_based モードではリスク% とストップロス% に基づく株数算出を実装。

- 研究・ファクター
  - research/factor_research.py:
    - DuckDB 接続を受け取り、prices_daily テーブルを参照してファクターを計算。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range を厳密に扱う）、相対 ATR、20日平均売買代金、出来高比率等を計算（詳細は実装参照）。
    - 大きなウィンドウや null の取り扱いに注意した実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を調整するユーティリティを追加。
      - Windows: psutil の PRIORITY_CLASS 値を使用（getattr によるフォールバック）。
      - POSIX: nice 値で high=-10 / normal=0 / low=10 を設定。
      - アクセス権限不足等は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留めする機能を追加（対応 OS は psutil がサポートする範囲）。例外時は警告でスキップ。

### Changed
- （初回リリースのため、既存コードからの差分としての変更点はありません）

### Fixed
- （初回リリースのため、既知バグ修正はありません）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- run_monitoring / run_execution は停止フラグ（data/stop_requested.flag）や PID / kill flag 関連の設計を含み、運用時の安全停止フローを考慮しています。
- .env の取り扱いにおいては「.env を絶対に Git にコミットしない」旨が config_setup の生成ファイルに明記されています。
- 本 CHANGELOG はコードベースのコメント・実装から推測して作成しています。実際の設計意図や外部 API 実装（BrokerClient 等）については別ドキュメントや実装コードを参照してください。
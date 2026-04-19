# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  
参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回公開リリース。

### 追加 (Added)
- 基本アプリケーション設定管理
  - Settings クラスを導入し、環境変数から各種設定（J-Quants / kabuステーション / DB パス / ログ等）を取得可能にしました。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。これにより .env の自動読み込みが CWD に依存せず動作します。
  - .env 自動ロードの挙動:
    - 読み込み順: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサを独自実装:
    - export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。

- 起動スクリプト / デーモン化補助
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックしログに警告を出力。
    - 監視は常に production の sqlite_path を使用（環境に依存せず監視用 DB を参照）。
    - stop_requested.flag による外部停止フラグに対応。
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB から分離。
    - BrokerClientFactory を利用して paper/live に応じた Broker クライアントを生成。
    - エンジンは別スレッドで実行し、stop_requested.flag により停止を検知して安全に停止処理を行う。
    - PID ファイル出力に対応。

- ログおよびプロセス管理ユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテーション、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収してカレントプロセスの優先度設定を行う（high/normal/low）。
    - set_cpu_affinity(cpu_count): 指定したコア数にプロセスを固定（サポート外 OS はスキップ）。権限不足等は警告でスキップ。

- 設定支援 CLI
  - config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目はマスク表示、既存値の再利用、デフォルト値提示などに対応。.env の書き込みを行う。
  - validate_config.py:
    - .env と config/*.yaml の検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config YAML の存在・パース検証（PyYAML があればパースチェックを実行）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選別。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックして候補を除外する機能（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）に基づくスケーリング処理を実装。
    - aggregate cap 超過時のスケールダウンロジックと remainder による追加配分ロジックを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究・分析ユーティリティ（骨組み）
  - research.factor_research:
    - DuckDB 接続を受け取り momentum 等のファクターを計算する設計の骨組みを追加。複数の定数（窓長等）と calc_momentum の初期実装を含む（一部未完）。

- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、遅延 (avg/max/P95)。
    - デフォルト基準値（PASS/FAIL）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to) と --db オプションに対応。

### 変更 (Changed)
- —（初回リリースのため過去リリースからの変更はありません）

### 修正 (Fixed)
- —（初回リリースのため過去バグ修正履歴はありません）

### 既知の制約 / TODO
- research.factor_research の実装は途中（calc_momentum の途中でファイルが切れている）。今後のリリースで完全実装予定。
- position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的には前日終値や取得原価などのフォールバック価格を導入予定（TODO コメントあり）。
  - lot_size は現状全銘柄共通の固定値（将来的に銘柄別対応を検討）。
- .env の自動読み込みはプロジェクトルートが検出できない場合にスキップされる点に注意。
- 一部のシステム機能（プロセス優先度設定、CPU affinity、ファイルハンドラ作成）は権限や OS に依存するため、実行環境によっては無効化され警告ログが出力されます。

### 互換性と注意点
- 監視（run_monitoring）は常に Settings.sqlite_path を使用します。paper_trading 環境でも本番監視 DB を参照する設計になっているため、運用時は意図を確認してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper 専用 DB を使用するため、本番データと分離してペーパートレードが可能です。
- ロギングは標準で stdout に出力するため、cron 等での利用時に stdout/stderr のリダイレクト設定を考慮してください。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして公開する前に内容を確認のうえ必要に応じて修正してください。）
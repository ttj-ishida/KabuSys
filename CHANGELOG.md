CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

- なし（新規リリース v0.1.0 にて実装済みの機能を記載）

[0.1.0] - 2026-04-17
--------------------

初回公開リリース。主な実装内容と注意点をまとめます。

Added
- 基本構成・バージョン
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージの公開 API を `kabusys.__init__` に定義（data, strategy, execution, monitoring をエクスポート）。

- 設定・環境管理
  - Settings クラスを実装し、環境変数から各種設定値を取得可能に。
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値など多数のプロパティを提供。
    - KABUSYS_ENV、LOG_LEVEL 等の検証を行い、不正な値は例外を送出。
    - paper_trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
  - 自動 .env ロード機能を実装（プロジェクトルートが検出できれば .env/.env.local を読み込み）。
    - OS 環境変数を保護する仕組み（protected）を導入。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークンなど）
    - 保存前の確認、既存値の再利用、シークレットマスク表示などをサポート。

- 設定検証 CLI
  - validate_config モジュールを実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行・監視プロセス起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite を使用（本番 DB と完全分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine 起動・停止制御。
    - プロセス優先度を起動時に "high" に設定（set_process_priority を呼び出す）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全シャットダウン処理。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度を "high" に設定、停止フラグでループ終了。

- 監視 DB 初期化
  - monitoring_db の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring の起動処理に組み込み（冪等な初期化を保証）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（signal_rank をタイブレークとして使用）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み計算。全スコアが 0 の場合に等金額へフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックにより候補を除外（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返却（bull/neutral/bear をサポート、未知レジームはフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: 配分方法（risk_based / equal / score）に基づく株数決定ロジックを実装。
      - lot_size（単元）で丸め、注文数は既存ポジションを考慮して増加分のみ算出。
      - per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
      - スケールダウン後の端数は再分配ロジックで lot 単位で補正。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離率を DuckDB の prices_daily テーブルから計算。
      - 必要な過去範囲は安全マージンを持って取得（スキャン日バッファ）。
      - データ不足銘柄は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率などの計算（部分窓に対応）。
    - DuckDB 接続を受け取り SQL で効率的に計算する設計。

- ツール
  - tools.paper_verification_report: ペーパートレード向け検証レポート生成スクリプトを追加。
    - デフォルト DB は data/paper_trading.db（環境変数で上書き可）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を抽出して PASS/FAIL 判定を行う。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収して現在プロセスの優先度（high/normal/low）を設定。権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count): プロセスの CPU affinity を最初の N コアに固定。未サポート環境や権限不足時は警告でスキップ。
    - psutil を使用。

Changed
- なし（初回リリースのため、既存仕様変更はなし）

Fixed
- なし（初回リリースとしてバグ修正履歴はなし）

Notes / 注意事項
- Paper Trading と Live の DB は分離される設計になっているため、本番データとテストデータが混在しないように注意：
  - paper_trading 環境では `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用。
  - monitoring は設計上、本番の sqlite_path を参照するため、監視データ取り扱いに注意が必要。
- run_execution / run_monitoring は停止フラグファイル（data/stop_requested.flag）を介して外部から終了指示を受け付ける。
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意書き有り）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML）が必要：
  - PyYAML がない場合、validate_config の YAML 検証はスキップされ、警告が出る。
  - psutil 権限がない場合、優先度設定や affinity 設定はスキップされる（警告ログ）。

Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する設計。
  - config_setup はそれらをシークレットとして扱い、表示時にマスクする。
  - .env ファイルは Git にコミットしないよう明確にドキュメント化済み。

References / 次のステップ提案
- ドキュメント: PortfolioConstruction.md / StrategyModel.md 等の参照がコード中に出てくるため、これらの関連ドキュメントをリポジトリに揃えると理解が容易になります。
- テスト: position_sizing のスケーリングや apply_sector_cap の境界条件についてユニットテストの追加を推奨します。
- エラーハンドリング: run_monitoring のループ内での例外はログして継続する設計だが、重大エラー時のアラート送信（LINE など）連携を検討。

---
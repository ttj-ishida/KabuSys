# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 初回リリース
初期リリース。システム全体の基盤となる設定管理、起動スクリプト、ポートフォリオ構築ロジック、ポジションサイズ計算、リスク調整、リサーチ用ファクター計算、ユーティリティ、検証・ウィザード・集計ツールなどを含みます。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - DuckDB と SQLite を組み合わせたローカル分析／監視基盤をサポート。

- 設定管理
  - 環境変数・.env の自動読み込み機構を実装（kabusys.config）。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行う（CWD 非依存）。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数保護）を実装。
    - 値のパースはクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを実装し、主要な設定（J-Quants、kabu API、DB パス、Paper Trading 設定、監視閾値など）をプロパティ経由で提供。
  - PAPER_FILL_MODE のバリデーション、Paper Trading 用 SQLite パス、各種閾値やフラグのデフォルト値を定義。

- 設定ツール
  - 対話式設定ウィザードを追加（kabusys.config_setup）。
    - .env の初回作成・更新を対話形式で支援。
    - シークレットのマスク表示、選択肢・デフォルト表示、保存前の確認を実装。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ループを実装。
    - 停止フラグ（data/stop_requested.flag）検出により安全に停止する仕組み。
    - 起動時にプロセス優先度を High に設定（set_process_priority を使用）。
  - 監視ポーリング起動スクリプトを追加（kabusys.run_monitoring）。
    - SystemMonitor を用いたポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動を明示。
    - 停止フラグ検出でループを終了、例外はログ出力して次ポーリングへ継続。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順（同点時は signal_rank）で上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有セクター比率が上限を超えている場合に新規候補を除外（"unknown" セクターは除外適用外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告と共に 1.0 でフォールバック。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - リスクベースの許容リスク率、損切り率、単元株丸め（lot_size）、1 銘柄上限・全体利用率上限、手数料・スリッページの保守的バッファ（cost_buffer）を考慮。
    - aggregate cap により合計投資が available_cash を超える場合はスケールダウンし、端数は lot_size 単位で残差分を大きい順に再配分するロジックを実装。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - DuckDB 接続を受け取り prices_daily テーブルを参照してファクターを計算（外部 API にはアクセスしない設計）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。十分なデータがなければ None。
    - calc_volatility: ATR、相対 ATR、20 日平均売買代金、出来高比等を計算（実装の一部がファイル末尾で継続）。
    - 計算は target_date を基準に過去一定日数をスキャンする方式。パフォーマンスを考慮した SQL を使用。

- ユーティリティ
  - プロセス優先度 & CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定（psutil を利用）。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能。入力検証と例外時の警告を実装。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH を指定するか --db オプションで DB を指定して、稼働率・注文成功率・送信率・API レイテンシ（P95 など）を集計。
    - 基準値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）をサポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

利用上の注意・補足
- 環境変数自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- run_monitoring は監視用の sqlite_path を本番設定（Settings.sqlite_path）から参照します。環境に関係なく監視 DB を共有しない運用をする場合は設定を適宜変更してください。
- process_priority / cpu_affinity は psutil に依存します。psutil が利用できない環境や権限がない場合は警告が出力され、処理は継続します。
- config/*.yaml の内容検証は PyYAML の有無に依存します。PyYAML がない場合は存在チェックのみ行われ、詳細パース検証はスキップされます。

（この CHANGELOG はコードベースから推測して作成した変更履歴です。実際のリリースノートとして使用する際は必要に応じて調整してください。）
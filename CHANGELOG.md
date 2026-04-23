# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

なお、本 CHANGELOG はリポジトリ内のコード内容から変更点・機能を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - ブローカークライアントの生成を BrokerClientFactory に委譲。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。デーモンスレッドでセッションを実行し、外部停止フラグで安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - 実行中の PID ファイル管理（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値は警告のうえデフォルトにフォールバック）。
    - 監視（monitoring）については KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- 設定関連
  - config.py
    - Settings クラスを導入し、各種環境変数の一元管理を実装（J-Quants / kabu / LINE / DB / 監視閾値 / システム設定 等）。
    - .env 自動ロード機能を実装（プロジェクトルート検出 .git / pyproject.toml 基準）。.env/.env.local 読み込み順序、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の紙トレードや Kill Switch 関連設定を追加。
    - env 値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL など）。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - J-Quants トークンや kabu API パスワードなどの必須項目、既存 .env の読み込み・既存値の再利用、シークレットマスキング表示、保存前確認などを実装。
    - .env を書き出す際に注意書き・テンプレートを付与。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性確認、DB パスの親ディレクトリ確認、YAML ファイル存在／パース検査（PyYAML がない場合は警告してスキップ）、本番環境用の追加ガード（LINE 通知未設定や Kill Flag の自動クリア設定に対する警告）等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（タイブレーク: signal_rank 昇順）で選出。
    - calc_equal_weights: 等金額配分計算。
    - calc_score_weights: スコア比率で正規化して重みを算出。全スコアが 0 の場合は等配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮してセクター集中上限を適用し、新規候補をフィルタリング（"unknown" セクターは対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告してフォールバック 1.0。

  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分／スコア配分／リスクベース（risk_based）等の割当方式に対応し、各銘柄の発注株数を計算。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）を適用。コストバッファを使った保守的見積りと、スケールダウン時の端数調整ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows の priority class / POSIX の nice を扱う）。
    - set_cpu_affinity による CPU ピニング機能も追加。
    - 権限不足や未対応 OS の場合は警告してスキップ。

- モニタリング / DB 初期化
  - monitoring/monitoring_db の初期化呼び出しを実装し、起動スクリプトから監視用テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（既定 data/paper_trading.db）からデータを集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出するレポートを追加。
    - PASS/FAIL の閾値（稼働率 99%、成立率 90%、送信率 95%、P95レイテンシ 200ms）を定義。
    - 日付フィルタ（--from / --to）および --db オプションをサポート。

- リサーチ（ファクター計算）
  - research/factor_research.py を追加（Momentum / Value / Volatility / Liquidity 指標の計算モジュールの骨格）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照し、モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高系指標等を算出する設計（関数群の導入、定数定義、calc_momentum の実装開始）。ファイル末尾で切れている（開発中の箇所あり）。

### Changed
- ロギングに関する挙動
  - コンソール出力は stdout を利用する設計へ変更（cron 等でのリダイレクト運用を考慮）。
- 起動時のプロセス優先度
  - 起動スクリプト（execution / monitoring）で最初に set_process_priority("high") を実行しているため、デフォルトで優先度を高くする運用想定。

### Fixed / Notes
- .env 読み込みの堅牢性向上
  - export プレフィックス対応、クォート内のエスケープ処理、コメントの解釈ルールなどを実装し、.env のパースをより現実的な形に改良。
- validate_config の挙動
  - PyYAML 未導入時は YAML パースチェックをスキップして警告を出力。設定ファイルが存在しない場合は生成スクリプトの利用を案内するメッセージを出力。
- 安全設計
  - run_execution/run_monitoring ともに停止フラグ（data/stop_requested.flag）を検出して graceful shutdown する仕組みを実装。
  - run_execution は起動前に停止フラグが既に立っている場合は起動せずに終了する保険を追加。

### Known limitations / TODO
- research/factor_research.py の一部（calc_momentum 等）が途中で切れており、実装完了が必要。
- position_sizing の価格欠損（price が 0.0）時のフォールバック戦略（前日終値や取得原価使用など）は TODO コメントとして残っている。
- 将来的な拡張として銘柄ごとの lot_size を持たせる設計（stocks マスタ参照）を想定している。

---

もし詳細なリリース日やバージョニング方針、あるいは追加の変更履歴（過去のコミット単位での差分）を反映したい場合は、該当するコミットメッセージや差分を提供してください。それに基づいてより正確な CHANGELOG を生成します。
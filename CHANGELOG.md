# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

最新: Unreleased
履歴: 0.1.0 — 2026-04-17

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
初回リリース — 基本的な自動売買フレームワークと運用ユーティリティを実装しました。

### Added
- プロジェクト全体のバージョン番号を追加
  - src/kabusys/__init__.py: __version__ = "0.1.0"

- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV に応じて本番用 SQLite とペーパートレード用 SQLite (data/paper_trading.db) を切替。
    - paper_trading 環境では MockBrokerClient を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱いを実装。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視では KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは一貫して同一 DB に格納）。
    - 停止フラグの検知と例外発生時のロギングを実装。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメントなどに対応。
    - 各種設定プロパティ（DB パス、PID・KILL フラグ、監視閾値、paper_trading 用設定、ログレベル判定、env 判定など）を実装。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。
    - 入力項目の定義、既存 .env 読み込み、マスク表示（シークレット）、確認プロンプト、.env ファイル書き込みを実装。
    - デフォルト値、選択肢、説明文を備えた質問リストを提供。

  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を実装（--strict オプションで警告を FAIL 扱いにできる）。
    - 必須 / 任意の環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの存在確認（親ディレクトリ）、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けガード（LINE トークン・KILL フラグ設定）を実装。
    - 検証結果を INFO / WARNING / ERROR に分類して出力し、終了コードを返す。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度 (high/normal/low) と CPU affinity のユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収する実装。psutil を使い、権限・未対応 API の場合は警告を出して安全にスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定と重み計算用の純粋関数を提供:
      - select_candidates: スコア降順 + signal_rank で上位 N を選択
      - calc_equal_weights: 等金額配分
      - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームは 1.0 でフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ計算を実装（risk_based / equal / score の配分方式をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金 available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。
    - risk_based では許容リスク率 risk_pct と stop_loss_pct を用いてベース株数を計算。
    - スケールダウン時の残差取り扱い（lot 単位で再配分するロジック）を実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をまとめてエクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials のテーブルに基づきファクターを計算する純粋関数群を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などを計算（データ不足に配慮）。
    - 設計上、外部 API へはアクセスせず DuckDB の SQL と Python ロジックで計算する。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 の計算、日付フィルタ (--from / --to)、DB パス指定 (--db / 環境変数) をサポート。
    - 基準値（閾値）を定義し、PASS/FAIL を出力。テーブル欠如に対しては例外を捕捉して N/A を扱う。

- 監視用 DB 初期化呼び出し
  - src/kabusys/monitoring/...（個別ファイルは参照されているがここでは外部実装）：run系スクリプトから init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を統合。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布パッケージなどでプロジェクトルートが見つからない場合は自動ロードをスキップする設計です。
- run_monitoring と run_execution は共にプロセス優先度を最初に "high" に設定しようとしますが、権限や OS によっては設定に失敗して警告が出力されます（処理は継続します）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番データベースと完全に分離される想定です。PAPER_TRADING_SQLITE_PATH や PAPER_FILL_MODE で挙動を調整できます。
- position_sizing や risk_adjustment の関数群は純粋関数（副作用なし）として設計され、単体テストしやすい構成になっています。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出します。
- 実運用時は .env を絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書き有り）。

---
今後のバージョンでは以下の改善を予定しています（例）:
- 銘柄ごとの lot_size をマスターで管理する拡張。
- フォールバック価格の導入（price が欠損の際の扱い改善）。
- SystemMonitor / ExecutionEngine のより詳細な稼働メトリクスとアラート連携。
- テストカバレッジと CI の追加。
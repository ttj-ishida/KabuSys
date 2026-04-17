# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは、コードベース（src/kabusys 以下）の現在の状態から推測して作成しています。

全般的な注意
- 本リリースはパッケージの初期リリース相当（__version__ = 0.1.0）を想定してまとめています。
- 設定は主に環境変数（.env）で行います。自動読み込み・検証・ウィザード等のツールが用意されています。

## [Unreleased]
（次回リリース向けのメモ欄）

---

## [0.1.0] - 2026-04-17

### Added
- 基本実行スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データは本番DBを参照/記録）。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を使用）。
    - 停止はプロジェクトルート/data/stop_requested.flag を検出して行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に完全に分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）による安全停止、pid ファイル出力のサポート。

- 設定管理と補助ツール
  - config.py
    - Settings クラスを導入し、環境変数から設定を取得する一元化。
    - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 読み込み時に OS 環境変数を保護（既存値を protected として上書きを制御）。
    - 各種プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE（paper_trading 時の約定モード）検証（instant/partial/never/reject のみ許容）。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力対応。生成された .env を安全に書き出す。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および YAML パース（PyYAML が利用可能な場合）。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性を警告）。

- 運用・ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（および CPU affinity）を OS に依存せず設定するユーティリティを追加。
    - Windows（psutil の優先度クラス）、POSIX（nice 値）に対応。設定に失敗した場合は警告を出してスキップ。
    - set_cpu_affinity を提供（最初の N コアに固定する機能。失敗時は警告）。
  - monitoring/monitoring_db 初期化呼び出し（run_* スクリプトから使用）により、監視テーブルの存在を起動時に保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度に基づく候補除外（売却予定銘柄を計算から除外、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（既定値: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: ウェイト・候補・価格情報等に基づき発注株数を算出。
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score" をサポート。
      - lot_size（単元株）で丸め、max_position_pct（1銘柄上限）を考慮。
      - cost_buffer を使った保守的なコスト推定と、available_cash を超えた場合のスケールダウン（割合スケーリング＋端数配分のアルゴリズム）を実装。

- リサーチ
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: ATR（20日）、相対 ATR、20日平均売買代金、出来高比率等を計算（ウィンドウ内データ不足時は None）。
    - DuckDB 上の prices_daily テーブルを前提に SQL とウィンドウ関数で効率的に算出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）。
    - 主な指標・閾値:
      - 稼働率（uptime）閾値: 99.0%
      - 注文成功率（fill_rate）閾値: 90.0%
      - 送信率（send_rate）閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - システム安定性・注文成功率・リスク却下数・レイテンシ等をまとめ、PASS/FAIL 判定を出力。
    - P95 は独自実装（列表ソートから算出）。データがない場合は N/A 表示。

### Changed
- パッケージ公開情報
  - src/kabusys/__init__.py によりパッケージ名とバージョン（0.1.0）を定義。
- .env 読み込みロジックを堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - override フラグと protected セットにより OS 環境変数の上書きを安全に制御可能。

### Fixed
- なし（初期機能実装ベースのため明示的なバグ修正履歴はなし）。  
  実装上の注意点・既知の制約は下記「Notes」に記載。

### Notes / Breaking changes / 注意点
- 監視（run_monitoring）は「環境にかかわらず」本番用 sqlite_path（Settings.sqlite_path）を使用する設計になっています。監視データを別 DB に分離したい場合は運用上の配慮（パスの差し替え）またはコード修正が必要です。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB とデータを完全分離します。ペーパートレード時の DB はデフォルトで data/paper_trading.db です。
- .env の自動読み込みはプロジェクトルートが検出できない場合（.git も pyproject.toml も存在しない）にはスキップされます。テスト等で自動読み込みを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config._require は必須環境変数未設定時に ValueError を送出します（起動前の validate_config によるチェックを推奨）。
- utils/process_priority.set_process_priority と set_cpu_affinity は権限不足やプラットフォーム未対応時には警告を出し処理をスキップします。特権操作が失敗してもプロセス自体は継続します。
- position_sizing のスケーリングアルゴリズムは lot_size 単位で丸めるため、残余キャッシュの取り扱い等で微妙な差が生じます。将来的に銘柄別単元対応（lot_map）等の拡張が考慮されています。
- Paper Trading 検証レポートは SQLite のテーブル構造（system_status / trade_logs / risk_logs 等）に依存します。テーブルが存在しない場合は実行時に一部指標を N/A または 0 として扱います。

---

今後の改善候補（非包括的）
- run_monitoring/run_execution のログレベル・ロギング設定を Settings.log_level に基づいて初期化する。
- monitoring が本番 DB を直接参照している点を設定で上書き可能にする（運用の柔軟性向上）。
- position_sizing の lot_size を銘柄別に扱う拡張。
- factor_research のユニットテストとパフォーマンス検証（DuckDB クエリ最適化）。
- Paper Trading レポートの出力形式（CSV/JSON）や期間指定の改善。

（必要であれば、各ファイルごとの変更詳細（関数の引数仕様、戻り値の例、CLI の使い方の具体例）を追加で展開します。）
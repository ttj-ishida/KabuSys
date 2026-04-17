# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

現在のリリース
- [0.1.0] - 2026-04-17

## [0.1.0] - 2026-04-17
リリース: 初回公開。自動売買システム KabuSys のコア機能、CLI ツール、およびユーティリティ群を追加。

### 追加
- パッケージ基本情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- 環境設定・管理
  - .env の自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護しつつ .env / .env.local を読み込む挙動を実装（src/kabusys/config.py）。
  - .env パーサを実装。export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理などをサポート。
  - Settings クラスを追加し、環境変数を型ごとに安全に取得するプロパティを提供（J-Quants / kabuステーション / LINE / DB / 監視 / システム設定等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化できるオプションを追加。

- 対話式設定ウィザード
  - python -m kabusys.config_setup による .env 作成/更新ウィザードを追加（src/kabusys/config_setup.py）。
  - 項目定義、既存 .env 読み込み、マスク表示（シークレット項目）、保存確認を含む対話フローを提供。

- 設定検証ツール
  - python -m kabusys.validate_config による起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス（親ディレクトリ存在）・config/*.yaml の存在と YAML パース（PyYAML がある場合）などを検査。--strict オプションで警告を失敗扱いにできる。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine を組み立て、スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用し、監視用テーブルの初期化を実施。
    - プロセス優先度を上げて実行（utils の set_process_priority を利用）。

- モニタリング DB 初期化
  - init_monitoring_db を参照する実行フローの追加（run_monitoring / run_execution で呼び出し、監視テーブルの存在を保証）。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加し、ペーパートレードログ（SQLite）から稼働率・注文成功率・送信率・レイテンシ（P95 等）等を集計してレポート出力可能に。
  - 基準値（稼働率 99%, 注文成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）を定義し、Pass/Fail を判定するロジックを実装。
  - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio モジュールを追加（src/kabusys/portfolio/*）。
    - select_candidates: スコア降順、タイブレークに signal_rank を使用して候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分を実装。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、セクター限度を超えたセクターの候補を除外（"unknown" セクターは除外対象外として扱う）。
    - calc_regime_multiplier: market regime ('bull', 'neutral', 'bear') に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数計算を実装。lot_size（単元）、max_position_pct、max_utilization、cost_buffer に基づく aggregate cap のスケーリング処理や端数処理（lot_size 単位で丸め、残余を frac 大きい順に配分）を実装。

- ユーティリティ
  - process_priority ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。psutil を利用。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未実装機能は警告でフォールバック。

- リサーチ（ファクター計算）
  - research/factor_research.py を追加し、DuckDB 接続を使って以下のファクターを計算する関数を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None を返す）。
    - calc_volatility: ATR20、ATR 比、20日平均売買代金、出来高比率 等を算出する SQL ベースの処理（データ欠損制御を含む）。
  - 関数は prices_daily テーブルを参照し、結果を辞書リストで返す設計。

### 変更（設計上の注意 / フォールバック）
- .env ファイル読み込み
  - OS 環境変数はデフォルトで優先され、.env.local は .env の上書きとして読み込まれる（既存 OS 環境変数は保護）。
  - プロジェクトルートが見つからない場合は自動ロードをスキップ。

- Settings の検証
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値チェックを実装。無効値は ValueError を発生させることで起動前に誤設定を検出。

- run_execution / run_monitoring の動作
  - どちらの起動スクリプトも起動時にプロセス優先度を high に設定しようと試み、失敗した場合は警告で続行する。
  - 監視は本番用 sqlite_path を常に用いる設計。paper_trading は実行エンジン側で専用 DB に分離。

### 修正（バグ対応・堅牢化）
- MONITOR_POLL_INTERVAL のパースを堅牢化（不正値や 0/負値はデフォルト 60 秒にフォールバックして警告）。
- .env パーサでのクォート内エスケープ・インラインコメント処理の強化により、意図しないパーシングエラーを回避。
- DuckDB / SQLite を用いるレポート・ファクター計算関数で、テーブルが存在しない場合やデータ不足時に例外をキャッチして N/A / None を返すようにし、ツールが例外で落ちないように保護。
- process_priority/set_cpu_affinity で権限不足・未サポート OS に対して警告を出して安全にスキップするように修正。

### 既知の問題 / 注意事項
- portfolio.position_sizing の price の欠損（0.0）の場合、現状はエクスポージャが過小評価される可能性があり、将来的に前日終値や取得原価等のフォールバック価格を導入することを検討中（TODO コメントあり）。
- apply_sector_cap は "unknown" セクターの保護を行うが、マスタ不整合時の動作は要注意。
- run_execution はブローカーの実装に依存（BrokerClientFactory）。本番ブローカーとペーパーブローカー間のインターフェース整合が重要。

### BREAKING CHANGES
- なし（初回リリース）。

---

今後のリリースには、戦略ロジックの追加、単元ごとの lot_size 対応、より厳密な価格フォールバック、モニタリング/アラートの拡充（LINE 通知連携の実装）などを予定しています。
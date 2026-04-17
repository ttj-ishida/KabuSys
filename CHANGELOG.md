# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリース日はソースコードの参照時点です。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 実行用スクリプトを追加。
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor をポーリングするループを提供。停止はプロジェクトルートの data/stop_requested.flag で制御。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定。
    - monitoring 用 DB の初期化（init_monitoring_db）と DuckDB 接続を行う。Monitoring は環境に関わらず本番の sqlite_path を使用。
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するエントリポイント。Paper Trading 環境時は MockBrokerClient を使用し、専用の paper_trading DB に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカー生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動・停止制御（data/stop_requested.flag と execution.pid を利用）。
- 設定・環境系ユーティリティを追加。
  - Settings クラス (src/kabusys/config.py)
    - .env 自動ロード（プロジェクトルートの .env → .env.local、OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 各種環境変数へのアクセサ（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE 検証など）。
    - 環境 (development, paper_trading, live) / ログレベルの検証ユーティリティ。
  - 環境ファイルの対話式ウィザード (src/kabusys/config_setup.py)
    - .env の初期作成・更新を支援する対話式 CLI。シークレット項目は表示マスク。生成テンプレートの書き出し機能を提供。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数・パスの検証、config/*.yaml の存在確認および（PyYAML があれば）パース検証、`--strict` オプションで警告を失敗扱いにする機能。
- ポートフォリオ構築関連の純粋関数群を追加 (src/kabusys/portfolio)。
  - portfolio_builder
    - select_candidates, calc_equal_weights, calc_score_weights（スコア全0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap（既存保有を考慮したセクター上限フィルタ）、calc_regime_multiplier（レジームに応じた乗数、未定義レジームは警告してフォールバック）。
  - position_sizing
    - calc_position_sizes（risk_based / equal / score に対応、lot_size 単位丸め、aggregate cap スケーリング、cost_buffer 対応）。
- 研究・ファクター計算モジュールを追加 (src/kabusys/research/factor_research.py)
  - DuckDB 接続を利用したモメンタム・ボラティリティ等のファクター計算関数（calc_momentum, calc_volatility 等）。200 日移動平均、ATR、出来高系指標などを計算。
- 運用ツールを追加。
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
    - SQLite の paper_trading DB を読み込み、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計してレポート出力。閾値（稼働率 99%、成立率 90% 等）を定義して PASS/FAIL 判定を行う。コマンドラインで日付範囲指定や DB パス指定が可能。
- ユーティリティを追加 (src/kabusys/utils/process_priority.py)
  - プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定機能（psutil ベース）。プラットフォーム差分を吸収し、権限不足や未対応環境では警告を出してスキップ。

### 変更 (Changed)
- .env 読み込み挙動の強化 (src/kabusys/config.py)
  - .env のパース処理を堅牢化：`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープを考慮した解析、インラインコメント処理の改善。
  - .env.local は .env の上書き（override=True）で読み込む設計。
  - OS 環境変数は protected として上書きから保護。
- monitoring / execution の DB 接続ポリシー明確化。
  - run_monitoring は KABUSYS_ENV に関係なく production sqlite_path を使用して監視データを扱う。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する。

### 修正 (Fixed)
- run_execution / run_monitoring の起動/終了安全性を向上。
  - 起動直前に停止フラグ (data/stop_requested.flag) を確認し、既に立っている場合は起動を中止するようにした。
  - 監視ループ内で check_once() が例外を投げてもキャッチしてログに出力し、次のポーリングまで継続する設計。
  - 両スクリプトとも起動時にプロセス優先度を最初に設定するように明示（重要処理の前に優先度設定）。
- paper_verification_report の集計・表示の堅牢化。
  - データが不足する場合（テーブル未作成や該当期間データなし）に N/A を扱うようにし、OperationalError をハンドリングしてレポート生成が途中で失敗しないようにした。
  - P95 計算関数を実装し、P95 が求まらない場合は None を扱う。

### 注意事項 / 実装上の注記
- Settings.paper_fill_mode は "instant", "partial", "never", "reject" のみ有効。無効値は ValueError を発生させる。
- apply_sector_cap: sector が不明 ("unknown") の銘柄はセクター上限の適用対象外となる（ブロックされない）。
- calc_position_sizes:
  - 価格情報が欠損（0 や None）だと当該銘柄はスキップされる。
  - lot_size 単位で切り捨て / 再配分の際は安全弁として _max_per_stock を尊重する。
- process_priority / set_cpu_affinity は psutil を利用しており、権限不足や非対応プラットフォームでは警告ログを出すのみで処理を継続する。
- 自動 .env 読み込みはプロジェクトルートが特定できた場合のみ実行される（.git または pyproject.toml を基準に探索）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 設定検証 CLI は PyYAML が存在しない場合、YAML の内容検証をスキップして警告を出力します。

### 既知の制限 / TODO
- position_sizing の lot_size は全銘柄共通で固定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap における price 欠損時のエクスポージャー過少見積りを防ぐためのフォールバック価格（前日終値や取得原価）の採用は未実装（TODO コメントあり）。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルに依存するため、テーブルスキーマ/データ準備が必要。

---

今後のリリースでは、単体テスト、型注釈の厳格化、Strategy/Execution の詳細実装（実取引向けブローカ実装やスリッページ・手数料モデルの強化）、および運用監視の強化（アラート送信・自動復旧）を予定しています。
# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは主にリポジトリ内の新規追加・設計方針・CLI/ユーティリティの挙動をコードベースから推測してまとめた初期リリース向けの変更履歴です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回公開リリース。以下の機能群を追加しました。

### 追加 (Added)

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。主な挙動:
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ監視を実装。
    - エンジン用 pid ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。主な挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告のうえデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず production の sqlite_path を使用して記録。
    - stop flag を検知すると監視ループを終了。

- 設定・環境管理
  - config.py: Settings クラスを追加。環境変数から設定を取得するユーティリティを提供。
    - .env/.env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パース機能: export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / paper_trading 用パス / 監視閾値 / 環境種別 / ログレベル等）。
    - PAPER_FILL_MODE の検証ロジック（"instant" / "partial" / "never" / "reject"）。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加（CLI）。出力は .env ファイル（テンプレートと注意文を含む）。既存値の再利用、シークレットマスク表示、保存確認を実装。

- 設定検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向け追加警告（LINE 設定や KILL_FLAG_CLEAR_ON_START）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的なロギング設定関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく解決ロジックを実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils/process_priority.py:
    - set_process_priority(level) を追加。Windows と POSIX 系の差分を吸収してプロセス優先度（nice / Windows priority class）を設定。
    - set_cpu_affinity(cpu_count) を追加。プロセスを最初の N コアに固定する機能（利用不可時は警告でスキップ）。
    - psutil を利用し、権限不足や未実装 API へのフォールバック（警告）を行う。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・タイブレークでソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）と候補除外ロジック。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0 / neutral:0.7 / bear:0.3、未知時は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。単元株丸め、1 銘柄上限、aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理を実装。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成 CLI を追加。指定期間（--from / --to）で SQLite（デフォルト data/paper_trading.db）から統計を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を表示。
    - P95 計算、各種クエリ（system_status / trade_logs / risk_logs）と欠損時の N/A ハンドリングを実装。
    - 判定閾値（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）は定数として埋め込み。

- パッケージ情報
  - __init__.py: パッケージのバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ に追加。

### 変更 (Changed)

- なし（初回リリースのため新規実装が中心）

### 修正 (Fixed)

- なし（初回リリース）

### 注意事項 / 設計上のポイント

- run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番監視 DB）を利用します。モニタは常に本番監視テーブルへ書き込む設計です。
- run_execution は paper_trading 環境時に専用の paper_sqlite_path を使い本番 DB と完全分離するため、ペーパートレードの結果は別 DB に記録されます。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされ、テスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- process_priority / cpu_affinity の変更は権限に依存します。権限不足や未対応プラットフォームでは警告を出し、処理をスキップします。
- portfolio モジュールは外部 DB に依存しない純粋関数として設計されています（単体テストしやすい）。

### 既知の TODO / 制約

- portfolio.position_sizing:
  - price が欠損（0.0）の場合のフォールバック価格ロジック（前日終値、取得原価等）について TODO コメントあり。
  - lot_size は現状グローバル共通の単元固定（将来的に銘柄毎の単元マスタに拡張予定）。
- research/factor_research.py はファクター計算モジュールとして追加されているが、ファイル末尾が途中で切れている（実装継続の必要あり）。

---

署名: 自動生成（コードベースの解析に基づく CHANGELOG）
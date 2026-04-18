# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※ この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴と差異がある場合があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。主要な機能追加と CLI / ユーティリティ群を導入。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - top-level の公開 API (`__all__`) に主要サブモジュールを追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止処理を実装。
    - 監視処理は環境にかかわらず本番用 SQLite パスを使用する仕様。
    - duckdb 接続および監視 DB 初期化処理を統合。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler 組立て、別スレッドでのエンジン実行・停止制御を実装。
    - 起動前に停止フラグが立っている場合は起動をスキップする安全処理を追加。
    - 実行時に PID ファイル管理（pid_file 指定）をサポート。

- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数をプロパティ経由で安全に取得。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env の読み込み順: OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を保護して上書き）。
    - .env 行パーサは export 形式、引用符つき値、エスケープシーケンス、インラインコメント等に対応。
    - 設定値の検証（env の有効性、LOG_LEVEL 値チェック、PAPER_FILL_MODE の妥当性チェック 等）。
    - 本番 / ペーパー / 開発判定を行うユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット値のマスク表示、選択肢やデフォルトの提示、保存確認を実装。
    - .env に書き出すテンプレートと注意書きを自動生成。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数・パス・YAML ファイル存在・本番向けガード等をチェック）。
    - --strict モードで警告も失敗扱いにできるオプションを実装。
    - PyYAML 未インストール時の処理スキップと警告出力を実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一されたログ設定ユーティリティを追加。
    - StreamHandler（stdout）および TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - 既存ハンドラの二重設定防止（既存ハンドラを flush/close のうえ再設定）を実装。
    - LOG_LEVEL / LOG_DIR / app_name による動作調整をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定を提供。
    - Windows 用の優先度クラスと POSIX の nice 値を内部でマッピング。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留めする機能を追加。
    - 権限不足や未対応環境時は警告ログを出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）: score 降順、同点は signal_rank 小さい順で上位 N を選択。
    - 重み計算:
      - calc_equal_weights: 等金額配分（1/N）。
      - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存ポジションと価格マップを使いセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知のレジームは 1.0 にフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・ポートフォリオ情報を元に発注株数を算出。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - リスクベース（risk_based）ではリスク許容率、損切り幅から個別目標株数を算出。
      - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファを考慮。
      - 合計投資額が利用可能現金を超える場合はスケールダウンし、残余キャッシュで残差配分を行うアルゴリズムを実装。
      - 価格欠損時のスキップや適切なロギングを実装。

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成するスクリプトを追加。
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数で代替可能）。
    - 指標・閾値:
      - 稼働率 (uptime) 閾値: 99.0%
      - 注文成立率 (fill rate) 閾値: 90.0%
      - 送信率 (send rate) 閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - system_status / trade_logs / risk_logs テーブルからの集計・P95 計算等を実装。
    - データ不足やテーブル未具備時の耐障害性（OperationalError を捕捉）を実装。

- 研究モジュール（不完全実装を含む）
  - research/factor_research.py
    - ファクター計算用モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。
    - calc_momentum の関数署名と定数群を追加（1M/3M/6M リターン、MA200 乖離、ATR など）。
    - DuckDB を利用した prices_daily / raw_financials 参照の設計方針を採用。
    - （ソース内で一部実装が未完了の箇所あり。引き続き実装予定。）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （該当なし）

### その他注意事項
- .env は秘匿情報を含むため、生成スクリプト内で「.env を絶対に Git にコミットしないこと」を明示しています。
- process priority / CPU affinity の設定は権限や OS に依存するため、失敗時は警告を出してスキップする安全な実装になっています。
- 監視（monitoring）処理は常に本番用 sqlite_path を使用する設計となっており、環境ごとの DB 分離が必要な場合は設定の見直しが必要です（現状は意図的に監視 DB を本番 DB と統一する仕様）。

---

本 CHANGELOG は現行ソースから推測して作成しています。必要に応じてリリースノートの細部を実際のリリースワークフロー（コミットログ・タグ）に合わせて更新してください。
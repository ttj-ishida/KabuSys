# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
メジャー/マイナー/パッチのポリシー (SemVer) に準拠します。

注: 以下はリポジトリ内のコードを解析して推測した変更点です（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ情報を追加
  - kabusys パッケージ初期バージョンを `__version__ = "0.1.0"` として導入。

- 環境設定 / ロード機能
  - Settings クラスを実装し、環境変数を統一的に取得する API を提供。
  - 自動 .env ロード機能を実装（プロジェクトルート (.git または pyproject.toml) を検出して `.env` と `.env.local` を読み込む）。OS 環境変数は保護され、`.env.local` は上書き可能。
  - .env のパースロジックを独自実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成・更新する CLI を追加。
  - シークレット値のマスク表示、選択肢・デフォルト提示、保存確認などの UX を実装。
  - デフォルト項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を定義して出力フォーマットで `.env` に書き込む。

- 設定検証ツール
  - `kabusys.validate_config`：起動前に環境変数や config/*.yaml を検証する CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース検証（PyYAML 未導入時は警告）等を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト
  - `run_execution.py` を追加。ExecutionEngine の起動手順を定義。
  - 起動時にプロセス優先度を設定 (`set_process_priority("high")`)。
  - Paper trading モード時は専用の SQLite DB を使用（`PAPER_TRADING_SQLITE_PATH` / `settings.paper_sqlite_path`）。
  - BrokerClientFactory を利用して本番/モックブローカーを切り替え。Engine をバックグラウンドスレッドで実行し、停止フラグ (data/stop_requested.flag) を監視して graceful shutdown を行う。
  - エンジン起動前に監視テーブルの初期化（冪等）を行う。

- 監視ループ起動スクリプト
  - `run_monitoring.py` を追加。SystemMonitor をポーリングで定期実行。
  - 起動時にプロセス優先度を設定。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値の場合はデフォルトへフォールバックし警告を出力。
  - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（監視は本番 DB を使う想定）。
  - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt による終了処理、DB 接続のクローズ処理を実装。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の履歴 DB を解析してレポートを出力。
  - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), レイテンシ (avg, max, P95) 等。
  - P95 計算、期間フィルタ (--from / --to)、DB パス解決ロジック（コマンド引数 > 環境変数 > デフォルト）を実装。
  - 合格/不合格判定基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms 等）。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`：候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。
  - `kabusys.portfolio.risk_adjustment`：セクター上限適用 (`apply_sector_cap`) と市場レジームに応じた乗数 (`calc_regime_multiplier`) を実装。
    - セクター不明 ("unknown") はセクター上限ルールの対象外とする。
    - レジーム乗数は `"bull":1.0, "neutral":0.7, "bear":0.3`、未知レジームは警告して 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`：銘柄ごとの発注株数算出 (`calc_position_sizes`) を実装。
    - 複数の allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、1 銘柄上限 (max_position_pct)、総投下上限 (max_utilization)、コストバッファ (cost_buffer) を考慮。
    - aggregate cap 超過時のスケールダウンと余剰分の lot 単位での再配分アルゴリズムを実装。
    - TODO コメントとして銘柄別 lot_size 対応や価格フォールバックの改善案を残す。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`：DuckDB を用いたファクター計算モジュールを追加。
    - Momentum（1M/3M/6M のリターン、MA200 乖離率）、Volatility（ATR, 相対 ATR, 平均売買代金、出来高比）等を SQL（DuckDB）で計算する関数を提供。
    - 入力は DuckDB 接続と target_date。結果は (date, code) キーの dict リストで返す。

- ユーティリティ
  - `kabusys.utils.process_priority`：クロスプラットフォームなプロセス優先度と CPU affinity 設定を追加。
    - Windows と POSIX (Linux/Mac 等) の差分を吸収（psutil を利用）。
    - `set_process_priority(level: "high"|"normal"|"low")`：アクセス権限不足などの場合は警告してスキップ。
    - `set_cpu_affinity(cpu_count: int|None)`：指定数で CPU affinity を設定（未対応環境では警告してスキップ）。
  - utils モジュールは上記機能を利用して起動時に優先度を上げる設計。

- モニタリング DB 初期化 API
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を参照するコードがあり、監視用テーブルの初期化を保証する仕組みが導入されている（冪等的に監視テーブルを作成する想定）。

### 変更 (Changed)
- なし（初回リリース想定）

### 修正 (Fixed)
- なし（初回リリース想定）

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- なし（コード解析からは明示的なセキュリティ修正は確認できません）。

---

備考:
- 本 CHANGELOG はソースコードからの推測に基づき作成しています。実際の開発履歴やコミットメッセージとは異なる場合があります。具体的な差分（コミット単位の履歴）が必要な場合は git ログ等の実データを提供してください。
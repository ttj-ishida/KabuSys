# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このプロジェクトではセマンティックバージョニングを採用しています。  

## [0.1.0] - 2026-04-18

初回リリース。主要な機能群とユーティリティを実装しました。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境設定 / ロード
  - .env ファイル自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml を基準）を実装。OS 環境変数は保護され、`.env.local` による上書きもサポート（src/kabusys/config.py）。
  - .env パースの挙動を細かく実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- 設定管理 API
  - `Settings` クラスでアプリ設定をプロパティとして提供（J-Quants / kabu API / DB パス / PID / モニタ閾値 / 環境種別等）。入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を含む（src/kabusys/config.py）。
  - `settings` シングルトンインスタンスをエクスポート。

- 設定ウィザード CLI
  - 対話式 `.env` 生成・更新ツールを追加（python -m kabusys.config_setup）。既存値読み込み、シークレット値のマスク表示、保存確認などを実装（src/kabusys/config_setup.py）。

- 設定検証 CLI
  - 起動前の設定検証コマンドを追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス/ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML 利用時）を行う。`--strict` オプションで警告を失敗扱いに可能（src/kabusys/validate_config.py）。

- 実行エンジン起動スクリプト
  - 実トレード/ペーパートレード対応の起動スクリプト `run_execution.py` を追加。`KABUSYS_ENV=paper_trading` の場合は専用の paper DB（`data/paper_trading.db` または環境変数で指定）および MockBrokerClient を使用して本番 DB と分離（src/kabusys/run_execution.py）。
  - Engine を別スレッドで実行し、`data/stop_requested.flag` による外部停止や PID ファイル管理をサポート。
  - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）と Reconciler / OrderManager 組立てを実装。

- 監視（Monitoring）起動スクリプト
  - `run_monitoring.py` を追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（src/kabusys/run_monitoring.py）。
  - 停止フラグ（data/stop_requested.flag）検知、例外発生時のロギング、プロセス優先度設定を含むポーリングループを実装。

- ペーパートレード検証レポート
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計・判定してレポート出力する CLI（期間指定オプションあり）。閾値による PASS/FAIL 判定を実装（src/kabusys/tools/paper_verification_report.py）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - 発注株数決定（calc_position_sizes）を実装。`risk_based` / `equal` / `score` の allocation_method、単元株丸め、aggregate cap のスケーリングロジック、cost_buffer を用いた保守的見積り、lot 単位での端数処理を含む（src/kabusys/portfolio/position_sizing.py）。
  - 上記をパッケージ出口としてまとめてエクスポート（src/kabusys/portfolio/__init__.py）。

- ログ設定ユーティリティ
  - `setup_logging` を実装。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日分保存）を設定。既存ハンドラのクリア、ログディレクトリ自動作成、環境変数/引数によるログレベル・ログディレクトリ解決を実装（src/kabusys/utils/logging_setup.py）。

- プロセス優先度 / CPU affinity ユーティリティ
  - `set_process_priority` と `set_cpu_affinity` を実装。Windows（psutil の優先度定数）／POSIX（nice 値）を吸収してクロスプラットフォームで優先度設定を試行。失敗時は警告して継続（src/kabusys/utils/process_priority.py）。

- 研究用ファクター計算（着手）
  - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、出来高系などの定義と calc_momentum の実装開始。src/kabusys/research/factor_research.py）。設計は prices_daily / raw_financials テーブル参照の純粋関数ベース。

### 変更
- なし（初回リリースにつき既存からの変更はありません）。

### 削除
- なし。

### 既知の制限 / 注意点
- run_monitoring は常に本番用の sqlite_path を使用する設計になっているため、ペーパートレード環境で監視データを分離したい場合は別途 DB 設定の調整が必要です。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別対応を検討）。
- factor_research の実装は一部で途中（calc_momentum の続きなど）であり、完全なファクターセットは今後拡張予定。
- .env の自動ロードはプロジェクトルートの特定に依存するため、配布後や特殊な配置で動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数を管理してください。

### セキュリティ
- .env ファイルは生成時に明示的に「Git にコミットしない」旨をコメントとして出力するようにしています（config_setup）。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の完成）。
- テスト追加（ユニットテスト / CI）とドキュメント拡充。
- ExecutionEngine / Broker クライアントのモック化と統合テスト。
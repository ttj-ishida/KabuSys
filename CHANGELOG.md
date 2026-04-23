# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、SemVer を想定しています。

## [未リリース]

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買フレームワーク「KabuSys」のコア機能とユーティリティ群を追加。

### 追加
- 基本パッケージとバージョン情報
  - パッケージのバージョンを `__version__ = "0.1.0"` に設定。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視は環境に依らず本番用の sqlite_path を使用して DB に接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient（ペーパートレード用）を使用し `data/paper_trading.db` に記録して本番 DB と完全分離。
    - 実行中の PID を data/execution.pid に書き、停止フラグで安全に停止可能。
- 設定管理
  - config.py
    - 環境変数読み込み / 管理クラス `Settings` を実装。
    - プロジェクトルート（.git または pyproject.toml）を基に .env 自動ロード（.env → .env.local、OS 環境変数を保護）。
    - 必須チェック（J-Quants / kabu API パスワード）、`KABUSYS_ENV` / `LOG_LEVEL` の検証、各種パス・フラグ取得を提供。
    - `paper_fill_mode`／`paper_sqlite_path` 等、ペーパートレード関連設定を提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 秘匿項目はマスク表示、既存 .env の読み込み・再利用をサポート。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、YAML パース等をチェック。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` による設定とデフォルト（INFO, logs/）をサポート。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows / POSIX）を追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 呼び出し側は OS を意識せず `set_process_priority("high")` などで使用可能。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分・スコア加重配分の計算（スコア全て 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率に基づき新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）：`bull`/`neutral`/`bear` をサポート（未知レジームは警告して 1.0 フォールバック）。
    - ドキュメントに設計上の注意（"unknown" セクター扱いや価格欠損の TODO）。
  - portfolio/position_sizing.py
    - 発注株数の算出ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - ロット（単元）丸め、1銘柄上限、集計上限（available_cash）に基づくスケーリング、コストバッファ考慮。
    - lot_size を単位として端数処理、残余キャッシュでの追加配分のアルゴリズムを実装。
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, cost_buffer）を引数で調整可能。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率、送信率、リスク却下数、API レイテンシ（平均／最大／P95）。
    - 判定閾値（デフォルト）を設定し PASS/FAIL を出力。
    - 日付レンジ指定（--from / --to）や DB パス指定（--db）をサポート。
- 研究用モジュール（骨格）
  - research/factor_research.py（ファクター計算のための下地）
    - Momentum / Value / Volatility / Liquidity などの計算設計を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する方針を記述。モメンタム計算関数の骨格が含まれる（実装途中のファイルあり）。

### 変更
- 初回公開のため履歴なし（新規追加のみ）。

### 修正（既知の注意点・TODO）
- portfolio/risk_adjustment.apply_sector_cap 内で価格欠損（price==0.0）時にエクスポージャーが過少見積りされる問題がコメントで指摘されており、将来的に前日終値等のフォールバック価格を導入する計画あり。
- position_sizing の将来的拡張として銘柄別 lot_size のサポート（stocks マスタへの移行）が TODO として記載。
- research/factor_research.py はファイル末端で途中（トランケート）しているため完全実装が必要。

### セキュリティ
- .env ファイルはデフォルトで自動生成されるものの、README 等で明示して .env を Git にコミットしないよう強調する文言を .env 生成ヘッダに含めています。

### 開発・運用メモ
- 環境変数自動ロードはデフォルトで有効。テスト等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視・実行の停止にはプロジェクトルートの data/stop_requested.flag ファイルを作成してください（run_monitoring/run_execution が検出して安全停止します）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や kill flag の設定に注意してください（validate_config が検出して警告します）。

---

今後のリリースでは、以下を優先して対応予定です（予定）:
- research モジュールの完全実装（ファクタ計算の完成・テスト追加）
- 銘柄別単元対応（lot_size の銘柄毎設定）
- 監視 / ロギングの強化（アラート送信・リトライ戦略）
- ドキュメント（運用手順、設計ドキュメント）の追加

もし CHANGELOG に含めたい変更点や既存の実装で正確に反映してほしい点があれば教えてください。
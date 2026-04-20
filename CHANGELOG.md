# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を想定しています。

## [0.1.0] - 2026-04-20

初期リリース。

### 追加
- 基本アプリケーション構成
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - プロジェクトルート探索ロジックを備えた環境設定モジュールを追加（src/kabusys/config.py）。
    - .env/.env.local の自動ロード（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env のパースで export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（スペース直前の `#`）に対応。
    - Settings クラスでアプリケーション設定をプロパティ経由で取得（J-Quants / kabu API / DB パス / PID / モニタ閾値 / 環境判定 等）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）をサポート。

- 起動用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し paper_trading.db にデータを記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - SQLite / DuckDB 接続の初期化、監視テーブルの冪等初期化を実行。
    - ExecutionEngine をデーモンスレッドで実行し、 data/stop_requested.flag の有無で安全に停止処理を実装。
    - PID ファイル管理（data/execution.pid）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視データを記録。
    - duckdb を分析用に接続。

- 設定関連ツール
  - 対話型環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env の初期作成・更新を対話式で支援。選択肢、デフォルト、シークレットマスク表示、保存確認を実装。
    - .env のテンプレート書き出し時に「.env を絶対に Git にコミットしないこと」を明記。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML が存在する場合）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険値を警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
  
- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）を設定。
    - LOG_DIR/LOG_LEVEL/引数指定からログ出力先・レベルを決定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを安全に閉じてから再設定するため二重ログ出力を防止。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度を設定。アクセス権限不足や未対応環境では警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する機能を提供（引数 None で無効化）。不正値は ValueError。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - portfolio_builder: 候補選定（score ソート）、等金額重み、スコア加重（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment: セクター上限の適用（当日売却予定銘柄は除外）、レジーム乗数 calc_regime_multiplier（bull/neutral/bear 支持、未知レジームは 1.0 にフォールバック）。
  - position_sizing: 銘柄ごとの発注株数決定（risk_based / equal / score）、単元株切り捨て、1 銘柄上限・aggregate cap（available_cash）・cost_buffer によるスケーリングと端数配分ロジックを実装。
  - portfolio パッケージ __init__ で主要関数を公開。

- ペーパートレード検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を抽出し、稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）などを算出してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定。
    - --from/--to/--db オプションで期間・DB パスを指定可能。

- DuckDB/SQLite 統合
  - DuckDB を分析用に接続する実装（run scripts と research モジュールで利用）。
  - 監視関連テーブルの冪等初期化用関数 init_monitoring_db を run スクリプトから呼び出すよう統合（監視/実行処理で共通利用）。

- 研究用ファクター計算モジュール（src/kabusys/research/factor_research.py）
  - Momentum / Value / Volatility / Liquidity 系ファクター計算を想定した設計と定数を追加（DuckDB 接続を受け取り prices_daily/raw_financials を参照）。（モジュールは部分実装）

### 変更
- なし（初期リリースのため新規追加のみ）。

### 修正（実装上の改善・注意点）
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のエスケープ、行内コメントの取り扱いなど実装。
- ロギング出力先は stdout を標準採用（stderr ではない）。cron / タスクスケジューラからのリダイレクトを想定。
- process_priority / set_cpu_affinity: 未対応プラットフォームや権限不足時に警告して処理をスキップする安全策を導入。

### 既知の制約・注意事項
- run_monitoring は監視データを常に本番 sqlite_path に記録します（KABUSYS_ENV に依存せず）。開発／テスト環境で使う場合は SQLITE_PATH を明示的に設定してください。
- PAPER_FILL_MODE の不正値は ValueError を送出します。PAPER_FILL_MODE は instant/partial/never/reject のいずれかで設定してください。
- position_sizing の price 欠損（0.0 または None）は現在はスキップ扱い。将来的にフォールバック価格を導入予定（TODO）。
- config_setup により生成される .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- research.factor_research.py は設計・定数を含むが、完全実装は今後の作業。

### マイグレーション / 利用開始メモ
- 初回セットアップ手順の例:
  1. python -m kabusys.config_setup で .env を生成/更新。
  2. python -m kabusys.validate_config で設定検証（本番では --strict 推奨）。
  3. 実行: python -m kabusys.run_execution（または run_monitoring）。
- 開発環境で自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper trading と本番の DB は分離されています。ペーパートレードを行う際は KABUSYS_ENV=paper_trading を設定してください。

---

（以降のリリースでは変更点をバージョン別に追記してください）
# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の指針に従って記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 初回リリース

公開日: 未設定

### 追加 (Added)
- パッケージ基盤を実装
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 実行用スクリプト・デーモン関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト下 `data/stop_requested.flag` ファイルの存在で検知。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する実装。
    - duckdb 接続を利用してモニタリングデータと連携。
    - monitor.check_once() 呼び出しで例外を捕捉して次のポーリングへ継続する耐障害性を確保。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用の Paper Trading 用 SQLite（`data/paper_trading.db` 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - ExecutionEngine をバックグラウンドスレッドで起動し、`data/stop_requested.flag` により停止制御。
    - エンジン PID ファイル出力機能（`data/execution.pid`）をサポート。
- 設定管理
  - config.py
    - 環境変数・設定読み込み用 `Settings` クラスを実装。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パースの強化: export 句対応、引用符内のエスケープ処理、インラインコメント処理など。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
    - `paper_fill_mode` の検証（有効値チェック）や Paper Trading 用 sqlite パス取得を実装。
- 設定補助ツール
  - config_setup.py
    - 対話式ウィザードで `.env` の初期作成・更新を支援。
    - 複数の設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / etc.）を対話で入力可能。
    - 既存 .env の読み込み、保存テンプレート生成機能を実装。
  - validate_config.py
    - 起動前チェック CLI を実装（必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース検証、live 環境向けのガード等）。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢性を実装。
    - ログレベルの解決順（引数 > 環境変数 > デフォルト）とログディレクトリの解決順（引数 > 環境変数 > default）を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（`set_process_priority`）と CPU アフィニティ設定（`set_cpu_affinity`）を実装。
    - アクセス権限や非対応環境では警告出力して安全にスキップする。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 (`select_candidates`) と配分重み算出（`calc_equal_weights`, `calc_score_weights`）を実装。
    - スコア全 0 の場合は等金額配分へフォールバックする警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を実装（既存保有を考慮して候補銘柄を除外）。
    - 市場レジームに基づく資金乗数 `calc_regime_multiplier` を実装（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - 各種配分方法（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限・合計利用可能現金に基づくスケールダウン（aggregate cap）、手数料・スリッページ見積り（cost_buffer）を考慮した配分調整を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を読み、システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を計算してレポートを表示する CLI を実装。
    - P95 算出、期間フィルタ（--from / --to）対応、指標の閾値に基づく PASS/FAIL 判定を実装（閾値はソース内定義）。
- 研究用モジュール（途中実装）
  - research/factor_research.py
    - DuckDB を使ったファクター計算基盤を追加（モメンタム・MA200・ATR 等の計算方針を実装予定）。
    - モメンタム計算関数 `calc_momentum` の骨組みを追加（実装途中でファイルが切れている）。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）

### 修正 (Fixed)
- 設定読み込み・パースの堅牢化
  - .env の行パースで引用符・エスケープ・インラインコメント・export 句等を正しく処理するよう改善。
- 実行スクリプトの堅牢化
  - run_monitoring のポーリング間隔環境変数が不正な値の場合にデフォルトへフォールバックして警告を出すように改善。
  - run_execution/run_monitoring で DB 接続やリソースを finally ブロックで確実にクローズするように改善。
  - ログファイル書き込みやプロセス優先度設定で失敗した際にフォールバックして続行する挙動を採用。

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- なし

注記:
- 一部ファイル（research/factor_research.py）は実装途中であり、完全実装は今後のリリースで提供予定です。
- 実行スクリプトはファイルベースの停止フラグ / PID ファイルを用いるため、運用環境ではこれらファイルの配置・権限に注意してください。
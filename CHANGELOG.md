# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般的な注意:
- デフォルト設定やファイルパスはコード内のデフォルトに基づき記載しています（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, logs/）。
- 環境変数で動作が切り替わる箇所が多数存在します。詳細は各項目の説明を参照してください。

## [0.1.0] - 初回リリース
(初期公開、機能実装)

### 追加 (Added)
- 基本的なアプリケーションパッケージ `kabusys` を追加。
  - パッケージのバージョンは `__version__ = "0.1.0"`。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定値（API トークン、DB パス、監視閾値、実行環境など）を取得するユーティリティを提供。
  - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む機能を追加。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` パースロジックは `export KEY=val` 形式、クォート値（エスケープ含む）、インラインコメントの扱いに対応。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式に `.env` を作成・更新するウィザードを実装。
  - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, 等）に対応。
  - 既存 `.env` の読み込みとマスク表示（シークレット項目）に対応。

- 設定検証ツール CLI
  - `kabusys.validate_config` を追加。必須環境変数やファイルパス、config/*.yaml の存在や YAML パース（PyYAML がインストールされている場合）などを検証。
  - `--strict` オプションで警告も失敗扱いにできる。

- 実行コンポーネント起動スクリプト
  - `kabusys.run_execution` を追加。ExecutionEngine を立ち上げる起動スクリプト（プロセス優先度設定、DB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler の組み立て、実行用スレッド管理、停止フラグ監視など）。
  - `KABUSYS_ENV=paper_trading` 時は paper trading 用 DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、Mock ブローカークライアントを利用する仕組みに対応。
  - 停止用フラグファイル（`data/stop_requested.flag`）と実行 PID ファイル（`data/execution.pid`）の扱いを実装。

- 監視コンポーネント起動スクリプト
  - `kabusys.run_monitoring` を追加。SystemMonitor のポーリングループ起動（プロセス優先度設定、DB 接続、監視 DB 初期化、ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` でオーバーライド可能、停止フラグ検知で終了）。
  - 監視は環境にかかわらず本番用の sqlite パス（`SQLITE_PATH` のデフォルト `data/monitoring.db`）を使用する仕様。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。stdout（StreamHandler）出力と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバックや二重設定防止を実装。
  - ログレベルの解決順、ログディレクトリの解決順を明確に実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定、CPU affinity を固定する関数 `set_cpu_affinity` を提供。psutil を利用し、権限不足などの際は警告を出してスキップする動作。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選択 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコアが全て 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有のセクターエクスポージャから上限超過セクターをブロック）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対する乗数を返す。未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 株数決定 `calc_position_sizes`（allocation_method に "risk_based" / "equal" / "score" をサポート、lot_size 単位で丸め、per-stock 上限・aggregate cap を考慮してスケールダウンを実施。cost_buffer による保守的推計を実装）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。paper_trading SQLite DB を読み取りシステム稼働率、注文成功率、送信率、P95 レイテンシなどを計算してレポート出力する CLI を実装。
  - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を実装。
  - 日付フィルタ（--from / --to）と DB パスの指定（--db / 環境変数）に対応。

- 研究用ファクター計算（下流処理向け）
  - `kabusys.research.factor_research` を追加（DuckDB 接続を受け取り、prices_daily/raw_financials を参照してモメンタム/バリュー/ボラティリティ/流動性等の算出を行う設計。モジュールは計算パラメータやスキャン窓を定義）。

- パッケージエクスポート
  - `kabusys.portfolio` のトップレベルで主要関数群を再エクスポート。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の制限 / 注意点 (Known issues / Notes)
- `.env` の自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配置方法によっては自動ロードされないことがある（その場合は環境変数を手動設定するか `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認）。
- `calc_position_sizes` の price 欠損時の扱いについて TODO コメントあり（将来的に価格フォールバックを検討）。
- `factor_research` モジュールの実装は設計方針や定数が含まれているが、部分的に未完（この CHANGELOG はコードの現状を反映）。
- 一部機能は外部モジュール（psutil、duckdb、PyYAML 等）に依存。これらがない場合は機能限定や警告によるフォールバックが行われる。

---

今後のリリースでは、ExecutionEngine / SystemMonitor 等の実装詳細、テストカバレッジ強化、エラー処理の拡張、設定ドキュメントの強化などを予定しています。
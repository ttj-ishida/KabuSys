# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このファイルは、配布されたコード内容から推測して作成した変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 初回リリース（推定）
リリース日: 未設定

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として導入。
  - モジュール群をエクスポート（data, strategy, execution, monitoring 等の想定トップレベル）。

- 設定 / 環境変数管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - .env パーサ実装: コメント、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ等に対応。
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数をサポート。
  - `Settings` クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
  - 各種設定プロパティ追加:
    - J-Quants / kabuステーション / LINE API 用設定
    - DB パス（DuckDB / SQLite）と paper trading 用 DB の分離 (`PAPER_TRADING_SQLITE_PATH`)
    - 監視・PID/kill flag 関連パス
    - 監視閾値（CPU / memory / disk）
    - 環境種別 (`KABUSYS_ENV`: development / paper_trading / live)
    - ログレベルの検証

- 設定関連 CLI ツール
  - `config_setup.py`: 対話式ウィザードで `.env` を作成・更新する CLI を追加。
    - シークレット入力、選択肢、既存値の再利用、保存確認をサポート。
  - `validate_config.py`: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行 / 監視用起動スクリプト
  - `run_execution.py`
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
    - `KABUSYS_ENV=paper_trading` の場合は paper trading 用 SQLite を使用して本番 DB と分離。
    - Broker クライアントを `BrokerClientFactory.create(settings)` で生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて `ExecutionEngine` を起動。
    - 停止フラグ（data/stop_requested.flag）検知でセッションを停止する機構。
    - 実行 PID ファイルの取り扱い（`data/execution.pid`）。
    - RiskManager のデフォルト設定 (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等) を定義。
  - `run_monitoring.py`
    - 監視ループ実装（SystemMonitor を使用）。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する（設計上の注意）。
    - 停止フラグ検出でループを終了。

- モニタリング DB 初期化
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を冪等に保証する処理を各起動スクリプトで実行。

- ロギング / プロセス管理ユーティリティ
  - `utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30 日保持）を設定。
    - ログディレクトリ自動作成、環境変数 `LOG_DIR` / `LOG_LEVEL` の尊重、ファイル作成失敗時のフォールバック動作を実装。
    - stdout を使用することで cron 等でのリダイレクト運用を想定。
  - `utils.process_priority`
    - Windows / POSIX に対応したプロセス優先度設定 (`high` / `normal` / `low`) を提供。アクセス権限や未対応プラットフォームに対しては警告を出してスキップ。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装（コア数チェック、例外時は警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`
    - シグナルの候補選択 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) 実装。スコア全0時のフォールバック（等配分）を警告する。
  - `portfolio.risk_adjustment`
    - セクター集中制限を行う `apply_sector_cap`（既存保有比率に応じて特定セクターの新規候補を除外、"unknown" セクターは無視）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバック）。
  - `portfolio.position_sizing`
    - 発注株数算出 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - リスクベース計算、単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ見積り）対応。
    - スケールダウン時の端数処理において lot_size 単位で再配分するロジックを実装。

- リサーチ / ファクター計算
  - `research.factor_research` の骨組みを実装（モメンタム、MA、ATR、ボラティリティ、流動性等を DuckDB 上の prices_daily / raw_financials テーブルから計算する設計）。（一部実装はファイル途中まで）

- Paper Trading 検証ツール
  - `tools.paper_verification_report.py`
    - paper_trading の SQLite DB を元にレポートを生成（システム稼働率、注文成功率 / 送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計）。
    - コマンドライン引数で期間指定（--from, --to）と DB パス（--db）を受け付け、環境変数 `PAPER_TRADING_SQLITE_PATH` と連携。
    - PASS/FAIL 判定基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms 等）および出力フォーマットを提供。

### 変更 (Changed)
- 起動・運用に関する設計方針の明示
  - 監視プロセスは監視専用 DB（SQLite）を使用し、環境変数にかかわらず監視 DB に対する操作は本番用パスを利用する旨のドキュメント（コード内コメント）。
  - logging ハンドラは既存ハンドラを一旦クリアしてから設定することで多重設定を防止。

### 修正 (Fixed)
- なし（初回リリース想定のため、既知のバグ修正は記載なし）

### 既知の注意点 / 今後の改善案（コード中の TODO）
- position_sizing, apply_sector_cap 等で価格が欠損（0.0）の場合の取り扱いが暫定的（将来的に前日終値や取得原価をフォールバックする案あり）。
- research.factor_research ファイルは実装が途中（ファイル末尾が途中で切れている）で、完全実装が必要。
- ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力にフォールバックするが、運用時の検知・通知フローの整備が望ましい。

---

注: 本 CHANGELOG は提示されたソースコードの内容から推定して作成したものであり、実際のリリースノートと完全に一致しない可能性があります。必要に応じて日付、著者、細かな実装差分を追記してください。
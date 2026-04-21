# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。
リリース日はリポジトリに含まれる現行ファイルの状態から推測して記載しています。

なお、この CHANGELOG はコードベース（src/ 以下）から推測して作成したものです。実際のコミット履歴に基づくものではありません。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定・管理
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得・検証可能に。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。`.env` → `.env.local` の優先度で読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化オプションをサポート。
  - .env ファイルのパース機能を強化（`export KEY=val`、クォートされた値、インラインコメントの扱いに対応）。
  - 必須環境変数取得時に未設定で例外を投げる `_require()` を実装。

- 設定支援ツール
  - 対話式 .env 作成/更新ウィザード（`kabusys.config_setup`）を追加。主要な設定項目（KABUSYS_ENV、J-Quants、kabu API、DB パス、LINE 通知、ログレベル、Kill Switch 等）を対話的に設定・保存可能。
  - 設定検証 CLI（`kabusys.validate_config`）を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、`config/*.yaml` の存在/パース（PyYAML がインストールされている場合）などをチェック。`--strict` オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定する機能を呼び出す。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）と MockBrokerClient を使用して本番 DB と完全分離する挙動をサポート。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイルの扱い、エンジンのデーモンスレッド起動／停止のループを実装。
    - リスク管理（RiskManager の設定）や OrderManager、Reconciler、ExecutionEngine の組み立てを行う。

  - 監視プロセス起動スクリプト `run_monitoring.py` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告出力。
    - 監視は環境に関係なく本番用の sqlite_path を使用して DB に接続し、監視テーブルの初期化を行う。
    - 停止フラグファイルを使った安全な終了検知、例外時のログ出力、接続クローズ処理を実装。

- 監視・運用ユーティリティ
  - 監視 DB 初期化ユーティリティ（`monitoring_db.init_monitoring_db` を参照）を使用して起動時に監視テーブルの存在を保障（冪等）。
  - 停止フラグ / PID / Kill Switch に関する構成項目を Settings に追加（`pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start` など）。

- ロギングとプロセス制御
  - 統一ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（ディレクトリ作成失敗時はファイル出力をスキップ）をルートロガーに設定。
    - ログディレクトリ、ログレベルの解決順を定義（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - CPU affinity 固定機能 `set_cpu_affinity` を提供。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数）
  - 候補選定と重み計算 (`kabusys.portfolio.portfolio_builder`)
    - BUY シグナルのスコア順ソート（同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - セクター集中制限とレジーム乗数 (`kabusys.portfolio.risk_adjustment`)
    - 同一セクターの既存保有比率が上限を超える場合に新規候補をフィルタする `apply_sector_cap`。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（`bull`/`neutral`/`bear` をマップし、未知は 1.0 にフォールバック）を実装。
  - 株数決定・単元丸め (`kabusys.portfolio.position_sizing`)
    - `risk_based` / `equal` / `score` に対応した発注株数計算を実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリングと残余配分ロジック）を実装。
    - 手数料・スリッページ見積のための cost_buffer パラメータをサポート。

- 研究モジュール
  - DuckDB を使ったファクター計算モジュール（`kabusys.research.factor_research`）を追加（モメンタム、MA200 乖離、ATR、出来高系等の計算を想定した設計と定数を含む）。SQL + Python で prices_daily / raw_financials を参照する方針。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）を追加。
    - Paper トレード用 SQLite DB（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - デフォルトの合格基準を定義（稼働率 >= 99%、注文成立率 >= 90% 等）し、PASS/FAIL を判定。

### 変更 (Changed)
- なし（初期リリースに相当する追加中心の変更）

### 修正 (Fixed)
- .env パースに関する堅牢性を向上
  - export プレフィックス対応、シングル/ダブルクォート中のエスケープ処理、クォートなし値のインラインコメント扱いの改善などを実装し、様々な .env 形式に対処。
- MONITOR_POLL_INTERVAL の不正値処理
  - 環境変数が不正（数値変換できない、0 以下など）の場合に警告を出しデフォルト値にフォールバックすることで time.sleep の例外を防止。
- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗しても stdout ログは継続されるようにして起動失敗を回避。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

既知の注意事項・設計メモ（コード内コメントからの抜粋）
- position_sizing の価格欠損時（price が 0.0）の扱いは現状簡略化されており、将来的に前日終値や取得原価等をフォールバックする可能性がある旨の TODO が残されています。
- risk_adjustment の apply_sector_cap は "unknown" セクターを上限チェック対象外とする仕様。
- calc_regime_multiplier は未知のレジーム値を見つけた場合に 1.0 でフォールバックして警告を出す設計。
- factor_research モジュールは DuckDB を前提に設計されており、prices_daily / raw_financials のスキーマ依存があるためデータ準備が必要。

もし実際のコミット履歴やリリース日・作者情報が必要であれば、git のログやリポジトリのタグ情報と照合して正確な CHANGELOG を生成できます。必要ならその手順を案内します。
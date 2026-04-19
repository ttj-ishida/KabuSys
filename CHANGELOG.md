# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
慣例: 重大な変更は Breaking changes として明示してください。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期版を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を設定。
- 実行・監視用起動スクリプトを追加。
  - run_execution: `src/kabusys/run_execution.py`
    - `ExecutionEngine` をスレッドで起動する CLI スクリプト。
    - Paper Trading 環境 (`KABUSYS_ENV=paper_trading`) の場合は専用の SQLite（デフォルト: `data/paper_trading.db`）を使用するよう分離。
    - 起動前に停止フラグ (`data/stop_requested.flag`) を確認し、存在する場合は起動を中止。
    - PID ファイル (`data/execution.pid`) のサポート。
    - プロセス優先度を "high" に設定（起動直後）。
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - `SystemMonitor` のポーリングループを開始するスクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視処理はプロダクションの sqlite パス（`Settings.sqlite_path`）を使用（`KABUSYS_ENV` に依存しない）。
    - 停止フラグ検出で安全にループ終了。
- 設定管理・自動読み込み機能を追加。
  - `src/kabusys/config.py`
    - .env 自動ロード機構（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - `.env` / `.env.local` の読み込み順制御、OS 環境変数の保護（既存キーを上書きしない/保護）。
    - 設定用 `Settings` クラスを提供（J-Quants, kabu API, DB パス, paper_trading 関連, 監視しきい値など）。
    - Paper Trading の振る舞い制御 `PAPER_FILL_MODE`（有効値: "instant" | "partial" | "never" | "reject"）を検証。
    - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev`。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
- 設定ウィザード CLI を追加。
  - `src/kabusys/config_setup.py`
    - 対話式に .env を作成・更新するウィザード。
    - J-Quants / kabu API など必須項目の入力、シークレットマスク表示、デフォルト値表示。
    - `.env` ファイルフォーマット出力（Git にコミットしない旨のヘッダを含む）。
- 設定検証 CLI を追加。
  - `src/kabusys/validate_config.py`
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスと config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 実行前に設定の健全性をチェックして起動ミスを防止。
- ロギングユーティリティを追加。
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通関数 `setup_logging()`。
    - ログ出力先ディレクトリ自動作成を試み、作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。
    - stdout を使用することで cron 等からの取り回しを考慮。
- プロセス優先度 / CPU affinity ユーティリティを追加。
  - `src/kabusys/utils/process_priority.py`
    - Windows/Linux/macOS の差異を吸収してプロセス優先度を設定する `set_process_priority(level)` を提供。
    - `set_cpu_affinity(cpu_count)` によるコア固定も提供（指定が無ければ何もしない）。
    - 権限不足や未サポート OS の場合は warning を出力して安全にスキップ。
- ポートフォリオ構築関連の純粋関数群を追加。
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)、等分配 (`calc_equal_weights`) 、スコア重み (`calc_score_weights`)。
    - スコアがすべて 0 の場合に等分配へフォールバックする警告あり。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 (`apply_sector_cap`): 既存保有のセクター比率が閾値を超えるセクターの新規候補を除外。
    - レジーム乗数 (`calc_regime_multiplier`): "bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは 1.0 でフォールバック（警告）。
    - 実装上の挙動と注意点（例: "unknown" セクター扱いは上限適用対象外）を明記。
  - `src/kabusys/portfolio/position_sizing.py`
    - リスクベース、等分/スコア配分に基づく株数計算 (`calc_position_sizes`) を実装。
    - 単元株（lot_size）に丸め、1 銘柄上限・アグリゲート上限のスケーリングロジック、手数料等を想定した cost_buffer、残差に基づく追加配分ロジックを実装。
    - 将来の拡張（銘柄別 lot_size）を想定した TODO コメントあり。
  - `src/kabusys/portfolio/__init__.py` で上記関数を公開。
- Paper Trading 検証レポート生成ツールを追加。
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH` / CLI `--db`) から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出してレポート出力。
    - 判定基準（閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算ロジック、日付フィルタリング（ISO8601 UTC 変換）および DB が欠損している場合の安全ハンドリングを実装。
- 研究用ファクター計算モジュールを追加（未完の関数あり）。
  - `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity 計算の設計と定数を記載。DuckDB を利用して `prices_daily` / `raw_financials` を参照する方針。
    - モメンタム計算用定数（1M/3M/6M 等）を定義中。calc_momentum の実装が途中（ファイル末尾が切れているため未完）であることを明示。

### 修正 (Changed)
- ログ出力の挙動:
  - ログハンドラの二重登録を防ぐため、既存ハンドラを flush/close してから削除する実装に変更（`setup_logging`）。
- .env パーサーの堅牢化:
  - 引用符付き値でのバックスラッシュエスケープ対応、インラインコメントの取り扱い、`export KEY=val` 形式への対応等を実装し、現実的な .env フォーマットを扱えるようにした。
- 環境変数自動読み込みの保護強化:
  - OS 環境変数は保護され、.env/.env.local からの上書き制御 (override 引数) を明確化。

### 既知の制限 / 注意点 (Known issues)
- `src/kabusys/research/factor_research.py` の `calc_momentum` 実装が途中でファイルが切れており、本機能は未完成。今後のリリースで実装を完了予定。
- `apply_sector_cap` 内で価格が欠損（0.0）の場合にエクスポージャーが過少評価され得る（TODO コメントあり）。前日終値や取得原価を使ったフォールバックの検討が必要。
- `position_sizing` の単元株 (lot_size) は現在全銘柄共通。将来的に銘柄別単位の対応を想定しているが現状未対応。
- `set_process_priority` / `set_cpu_affinity` は権限不足や OS 非対応時に実行できない場合があり、その場合は警告を出してスキップする（期待される挙動）。

### 開発・運用向けドキュメント補足
- 環境変数主要一覧（デフォルト値や用途）
  - KABUSYS_ENV: execution/monitoring の実行環境（development/paper_trading/live）
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 必須
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: デフォルト `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
  - LOG_LEVEL, LOG_DIR: ログ制御
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（デフォルト 60）
  - PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロード無効化フラグ
- 起動時の推奨手順:
  1. `.env` を作成（`python -m kabusys.config_setup` を推奨）
  2. `python -m kabusys.validate_config` で検証
  3. `python -m kabusys.run_execution` / `python -m kabusys.run_monitoring` を実行

---

今後の予定:
- research/factor_research の実装完了とテスト追加。
- 個別銘柄の lot_size 対応、price フォールバックロジックの追加。
- Execution/Monitoring の統合テストとドキュメント充実。

（この CHANGELOG は現行ソースコードの内容から推測して作成しました。実際のコミット履歴とは異なる場合があります。）
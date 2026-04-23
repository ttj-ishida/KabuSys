# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  

現在のバージョン: 0.1.0 — リリース日: 2026-04-23

## [0.1.0] - 2026-04-23
初回公開リリース

### 追加 (Added)
- 基本パッケージ情報
  - パッケージ名: KabuSys。バージョン: 0.1.0（src/kabusys/__init__.py）。
- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用の sqlite_path を使用する仕様。
    - 停止はプロジェクトルート/data/stop_requested.flag の存在検知で行う。
    - 起動時にプロセス優先度を "high" に設定する。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の MockBrokerClient を使用し、専用 DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）や実行 PID 管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定する。
- 設定管理
  - config.py
    - 環境変数の管理クラス `Settings` を追加。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパースは export 形式やクォート、インラインコメント等の一般的なケースに対応。
    - 多数の設定プロパティを提供: DB パス、LINE トークン、kabu API、各種閾値、環境判定（development/paper_trading/live）等。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）や Paper Trading 用 sqlite パスのプロパティを実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - インタラクティブな .env 作成・更新ウィザードを追加。
    - 必須項目（J-Quants トークン、kabu API パスワード等）やログレベル・DB パス等を対話式に入力可能。.env を書き出す `_write_env` を実装。
    - .env はコミットしないよう注記。
  - validate_config.py
    - 起動前の設定検証ツールを追加。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 利用。未インストール時はスキップ）を行う。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対してコンソール出力（stdout）と日次ローテートファイルハンドラを統一的に設定する `setup_logging` を追加。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 `LOG_DIR` > デフォルト "logs/"。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 日次ローテーション（30 日分保持）。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定 `set_process_priority(level)` を追加（"high"/"normal"/"low"）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を追加。
    - psutil を用い、権限不足や未対応 OS の場合は警告を出して安全にスキップする実装。
- ポートフォリオ構築ライブラリ (純粋関数群、DB 参照なし)
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 `select_candidates`（スコア降順、同点時は signal_rank のタイブレーク）。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等分フォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合は当該セクターの新規候補を除外。unknown セクターは上限適用除外）。
    - レジームに応じた乗数 `calc_regime_multiplier`（bull:1.0, neutral:0.7, bear:0.3。未知は 1.0 で警告）。
  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes` を追加。
    - allocation_method: "risk_based"（許容リスク率・stop_loss に基づく） / "equal" / "score" に対応。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、投下合計の aggregate cap、cost_buffer を考慮した保守的見積りとスケールダウン、端数配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - CLI オプション: --from / --to / --db。デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数 または data/paper_trading.db。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、API レイテンシ (avg/max/P95)。
    - デフォルト判定閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200 ms）。P95 計算実装あり。
- リサーチ（ファクター計算）
  - research/factor_research.py（設計とモーメンタム計算開始）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いて Momentum/Value/Volatility/Liquidity の計算を行う設計。
    - モメンタム計算 calc_momentum の骨組み（複数ハリゾンのリターン・MA200 乖離等）を実装（ファイル末尾で未完の箇所あり、続きあり）。

### 変更 (Changed)
- n/a（初回リリースのため変更履歴なし）

### 修正 (Fixed)
- n/a（初回リリースのため修正履歴なし）

### セキュリティ (Security)
- n/a（初回リリース時点で特筆すべきセキュリティ修正なし）

---

注意事項 / 補足
- .env に機密情報（J-Quants トークン、kabu API パスワード等）を保存するため、.env は Git にコミットしないでください（config_setup のヘッダに注記あり）。
- validate_config と config_setup は起動前に設定確認・整備を行うのに便利です。
- run_execution/run_monitoring はそれぞれ stop flag（data/stop_requested.flag）により外部から停止指示を受け付けます。
- process_priority や logging_setup は実行環境の差（権限・OS）に対して安全にフォールバックするよう設計されています。
- research/factor_research.py は設計方針と一部機能（モメンタム）を提供していますが、ファイル末尾が未完の箇所があります（今後の拡張を想定）。

今後の予定（例）
- research/factor_research の完全実装（残りファクター・正規化など）
- テスト追加（ユニットテスト・統合テスト）
- さらに詳細なドキュメント（PortfolioConstruction.md 等へのリンクやサンプル設定）

--- 

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。）
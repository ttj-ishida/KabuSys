# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。

### Added
- 実行スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトの data/stop_requested.flag を監視して行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB へ記録）。
    - 例外発生時はログに記録して次のポーリングまで待機。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（または環境変数で指定したパス）に完全分離して記録。
    - 起動時に data/stop_requested.flag を確認し、既に停止フラグがある場合は起動せず終了。
    - 実行はデーモン化スレッド上で run_session を実行し、停止フラグ検知で Engine.stop() を呼ぶことで優雅に停止。
    - 実行時にプロセス優先度を "high" に設定。

- 設定管理
  - kabusys.config.Settings
    - 環境変数から各種設定（J-Quants, kabuAPI, DBパス, PID/kill フラグパス, 監視閾値, 環境種別 等）を取得する Settings クラスを実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などの paper_trading 関連設定をサポート。
    - env の自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。読み込み順は OS 環境変数 > .env.local > .env（.env.local は override）。
    - 各種検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の制約など）を実装。
  - .env パーサの強化
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を正しくパース。
    - クォート無しの行でのインラインコメント判定（'#' の直前が空白またはタブの場合をコメントと判定）に対応。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を支援。
    - J-Quants、kabuAPI、DBパス、LOG_LEVEL、KABUSYS_ENV、KILL_FLAG_CLEAR_ON_START 等の主要設定項目を質問形式で入力・保存。
    - 保存前に確認表示を行い、シークレットはマスク表示。
  - validate_config.py
    - .env と config/*.yaml の前置検証 CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV 等の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無ければスキップして警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ログ / プロセスユーティリティ
  - logging_setup.py
    - 共通ログセットアップ関数 setup_logging を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL / app_name を優先順位に従って解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラを安全にクローズしてから再設定（多重設定防止）。
  - process_priority.py
    - カレントプロセスの優先度設定 set_process_priority(level) を実装（Windows と POSIX を吸収）。
    - CPU affinity を固定する set_cpu_affinity(cpu_count) を実装。
    - アクセス権限や未実装 API に対しては警告を出してフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群、DBアクセス無し）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートし top-N を選択（タイブレークロジックあり）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコア 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑制する候補フィルタリング（既存ポジションのセクターエクスポージャー計算、sell_codes を除外可能、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数 ("bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバック)。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき銘柄ごとの発注株数を決定。
    - lot_size 単位で丸め、max_position_pct/per-stock 上限、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積り、残余キャッシュに基づく優先配分ロジックを実装。
    - 価格欠損時のスキップや多層安全弁を備える。

- Research / ユーティリティ（部分実装）
  - research.factor_research
    - モメンタム・ボラティリティ等の因子計算基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計）。
    - モメンタム等の期間定数とスキャンレンジを定義（モジュール途中までの実装）。

- tools
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ（avg / max / P95）、リスク却下数 等を集計し PASS/FAIL を判定。
    - デフォルト閾値を定義（例: 稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - CLI 引数 --from / --to / --db を提供。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
    - DB に該当テーブルが存在しない場合は例外を捕捉して安全に N/A 扱い（OperationalError に対するフォールバック）。

### Changed
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" に設定（初期リリース）。

### Fixed
- （初回リリースにつき既知のバグ修正はなし）

### Security
- 機密情報の取り扱い
  - config_setup の出力 .env に対して「絶対に Git にコミットしないこと」とドキュメント化。
  - Settings は必須環境変数未設定時に ValueError を投げることで、意図しない秘密情報漏洩や未設定起動を防止する挙動を採用。

---

注意:
- 上記はコードベースから推測できる変更内容・機能の要約です。実行時の振る舞いや外部依存（psutil, duckdb, PyYAML 等）のバージョンや環境により挙動が変わる可能性があります。
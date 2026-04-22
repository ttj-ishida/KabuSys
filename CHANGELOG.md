# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日: 2026-04-22

## [0.1.0] - 2026-04-22

初回公開リリース。KabuSys のコア機能群（設定管理、起動スクリプト、ポートフォリオ構築ユーティリティ、監視・実行エンジンの起動補助、ロギング/プロセス制御ユーティリティ、検証ツール群、Paper Trading 検証レポート等）を含みます。

### 追加
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動/実行スクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する監視ループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非数）はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）に関係なく本番の `sqlite_path` を使用する点を明記。
    - プロセス優先度を最初に "high" に設定し、停止フラグファイル（data/stop_requested.flag）の検知でループ終了。
    - SQLite / DuckDB 接続の初期化とクリーンなクローズ処理を実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）。本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を利用。paper_trading 環境では MockBrokerClient を想定。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグ検知で安全に停止（pid ファイル管理含む）。
    - RiskManager（RiskConfig デフォルト設定）や Reconciler、OrderManager、OrderRepository の組み立てを行う起動フローを実装。

- 設定管理/ロード
  - config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。読み込み順は OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
    - 強化された .env パーサ（`_parse_env_line`）：`export KEY=...` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート。
    - `.env` 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）。
    - Settings クラスを提供し、必要な環境変数取得・検証プロパティを実装（J-Quants、kabuAPI、DB パス、paper_fill_mode チェック、PID/kill flag パス、閾値など）。
    - `paper_fill_mode` の有効値検証（"instant" | "partial" | "never" | "reject"）を追加。
    - `is_live` / `is_paper` / `is_dev` 判定プロパティを追加。

- 設定検証・ウィザード
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、YAML ファイル存在確認および PyYAML があればパース検証、KABUSYS_ENV=live の追加ガード（LINE 設定や Kill Switch 設定の警告）を実装。
    - `--strict` オプションで警告を FAIL 扱いにする機能を追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - シークレット項目は入力画面でマスク表示、既存 .env の読み込みと Enter で再利用、書き込みテンプレートに「.env を絶対に Git にコミットしないこと」を明記。
    - `--env-file` オプションで保存先を変更可能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - 既存ハンドラをクリアしてから再設定することで二重登録を防止。
    - ログレベル/ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プロセス優先度（set_process_priority）および CPU affinity（set_cpu_affinity）を設定するユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収する実装で、psutil を利用。必要な権限がない場合は警告ログを出してフォールバック。
    - 不正な引数チェック（例: cpu_count < 1）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）: スコア降順、同点は signal_rank の昇順でタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等配分にフォールバックし警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。既存保有を元にセクター比率を計算し、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing 実装（calc_position_sizes）。
    - risk_based（リスクベース）および equal/score（配分ベース）方式をサポート。
    - 損切り率/リスク率を考慮した株数算出、1 銘柄上限、lot_size（単元）丸め、cost_buffer（手数料/スリッページ見積）を考慮した aggregate cap（利用可能現金を超える場合のスケーリング）と余剰再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力、各種安全弁を実装。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率／注文成功率（Filled/Created）／送信率（Sent/Created）／リスク却下数／レイテンシ（avg/max/P95）を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db、`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可能。
    - P95 計算、日付フィルタ（ISO8601 UTC ベース）対応、各種データ欠損時のフォールバックを実装。

- 研究用ファクター計算（骨格/一部実装）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity 等のファクター計算を想定したモジュールを追加（設計コメントと定数、calc_momentum の実装開始を含む）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルに基づいて計算する設計。

### 変更
- 新規リリースのため該当なし（初回リリース）。

### 修正
- .env パーサの堅牢化（quote/escape/inline comment の扱い）により実運用での設定読み込みエラーを低減（config.py）。
- MONITOR_POLL_INTERVAL の不正値処理を厳格化し、0 以下や非数が指定された場合はデフォルトにフォールバックして警告を出力（run_monitoring.py）。
- ログ設定で既存ハンドラを確実に flush/close してから削除するようにし、再初期化時の二重出力を防止（utils/logging_setup.py）。
- process_priority / set_cpu_affinity での権限エラーやプラットフォーム非対応時に警告を出して安全にスキップ（utils/process_priority.py）。

### セキュリティ／運用上の注意
- config_setup が生成する .env テンプレートに「.env は絶対に Git にコミットしないこと」を明記。
- 本番運用時の注意点（validate_config の live guard）:
  - KABUSYS_ENV=live の場合、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定値に注意するよう警告を出すチェックを導入。
- 監視スクリプトは環境に関わらず本番用 monitoring DB（Settings.sqlite_path）を使う設計のため、運用時は DB パス設定に注意。

### 既知の制限 / TODO
- position_sizing の lot_size は全銘柄共通として実装。将来的には銘柄別単元情報を持たせる拡張が想定されている（TODO コメントあり）。
- apply_sector_cap の価格が欠損（0.0）の場合、エクスポージャーが過小評価される可能性があるため、将来的に前日終値や取得原価等のフォールバック価格導入を検討（TODO コメント）。
- research/factor_research はファイルの末尾が未完（calc_momentum の続きを想定）であり、追加のファクター実装・検証が必要。

---

今後の開発では、単体テストの追加、strategy/engine 周りの統合テスト、Research モジュールの完成、及びブローカーインタフェースの拡張（銘柄別 lot_size 等）を予定しています。
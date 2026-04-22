# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

最新リリース: 0.1.0

## [Unreleased]

（ここには次リリースでの変更を記載します）

---

## [0.1.0] - 2026-04-22

初回公開リリース。自動売買システム KabuSys の基礎機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・注意点です。

### Added
- 基本パッケージとバージョニング
  - パッケージメタ: kabusys.__version__ = "0.1.0" を追加。

- 環境設定・ロード
  - kabusys.config:
    - Settings クラスを導入。環境変数の取得・検証をプロパティで提供（J-Quants / kabu API / DB パス / モード等）。
    - プロジェクトルート自動検出機能（.git または pyproject.toml 基準）により .env/.env.local を自動ロード。
    - .env パース強化: export プレフィックス対応、クォート値のエスケープ処理、インラインコメント処理。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 環境セットアップ & 検証 CLI
  - kabusys.config_setup:
    - .env の対話式ウィザード（ウィザードでの読み取り・既存値の再利用、secret マスク、保存機能）。
    - .env ファイル生成／上書き機能（保存時に注意書き: .env を Git にコミットしないことを推奨）。
  - kabusys.validate_config:
    - 起動前に環境変数 / config/*.yaml / DB パス 等を検証する CLI。
    - --strict オプションで警告を失敗扱いにするモードを提供。
    - PyYAML が無ければ YAML 検証をスキップして警告を出す。

- 起動スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。プロセス優先度を「high」に設定。
    - 環境に応じて paper_trading 時は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper/live により Mock/実クライアントを切替想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）で安全に停止。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。プロセス優先度を「high」に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB で一元管理）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt に対応し DB 接続をクローズ。

- ログ & プロセス制御ユーティリティ
  - kabusys.utils.logging_setup:
    - コンソール（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）をルートロガーに設定するユーティリティ。
    - ログレベル / ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化して警告出力。
  - kabusys.utils.process_priority:
    - Windows / POSIX(Linux, macOS, FreeBSD) に対応したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity を提供（num コア指定）。権限不足または未対応環境では警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア順で上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を評価し、上限超過セクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に応じた投下資金乗数を返却（未知レジームは 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: weight / candidates / risk_based の複数配分方式を実装。lot 単位で丸め、per-stock 上限・aggregate cap（available_cash）を考慮。cost_buffer（手数料・スリッページ見積）を加味したスケーリングと残余配分ロジックあり。

- Paper Trading 検証ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計してレポート出力。
    - コマンドライン引数で期間（--from, --to）と DB パス（--db）を指定可能。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL を判定。

- research モジュール（ファクター計算）
  - kabusys.research.factor_research:
    - モメンタム等のファクター計算（モメンタム 1M/3M/6M、MA200 乖離、ATR、出来高指標等）を設計。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針を実装。
    - （注）ファイル冒頭では関数定義を始めているが、続き実装が途中で切れている箇所あり（コードベースに未完の可能性あり）。

- DB 接続
  - sqlite3 / duckdb を利用する設計を採用。監視・発注データは SQLite、分析は DuckDB を利用する想定。

### Changed
- （初回リリースのため「変更」はなし）

### Fixed / Improved
- .env 読み込みの堅牢化:
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートあり/なしで異なる挙動）を実装し、より現実的な .env フォーマットに対応。
  - .env.local は OS 環境変数（protected set）を上書きできるが、OS 環境変数は保護されるように実装。
- ログ設定:
  - 既にハンドラが設定されている場合はハンドラを flush/close してから再設定（重複設定防止）。
  - StreamHandler は stdout を使用（cron 等での出力リダイレクトを想定）。
- プロセス優先度設定でプラットフォーム差異を吸収（Windows 用定数がない場合は getattr でフォールバック）。

### Security
- .env ファイル生成時に「.env は絶対に Git にコミットしないこと」を明記。
- 必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings で未設定時に明示的にエラーを出す設計。

### Known issues / Notes / TODO
- research.factor_research の実装が途中で切れている箇所がある（ファイル末尾が不完全）。このモジュールは追加実装・テストが必要。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）した場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 銘柄ごとの単元株（lot_size）を将来的に stocks マスタで持つ拡張を想定する TODO がある。
- run_monitoring は「監視は本番 sqlite_path を使用する」設計としているため、監視データの DB 分離が必要な場合は運用ルールで対応する必要あり。
- process_priority / set_cpu_affinity は権限不足や OS 非対応時に警告を出してスキップする実装だが、期待通り動作するかは環境依存。

---

作成: 自動生成された変更履歴（コードベースの内容から推測）。実際のリリースノートとして公開する前に、プロダクトの運用者・開発者による確認・追記を推奨します。
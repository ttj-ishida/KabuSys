# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog 規約に準拠しています。  
バージョン番号はパッケージ内の __version__ を基準にしています。

※ 内容はリポジトリ内のコードを解析して推測した変更点・特徴をまとめたものです。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期リリース — 基本機能一式を追加。

### 追加 (Added)
- 実行/運用用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db を既定）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う仕組みを実装。
    - スレッドで engine.run_session を実行し、停止フラグ検知で安全に停止する。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。不正値は警告を出して既定にフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視情報を集中管理。
    - check_once() 実行時の例外をキャッチしてログ出力しループ継続する堅牢性を確保。

- 設定・環境関連
  - config.py
    - Settings クラスを導入し環境変数をラップ。多くの設定（DB パス、API トークン、しきい値、環境種別など）をプロパティで提供。
    - .env 自動ロード機能: プロジェクトルート（.git or pyproject.toml を探索）を基準に .env/.env.local を特定順で読み込み。既存 OS 環境変数を保護する仕組みあり。
    - .env パースで export プレフィックス、クォート文字、エスケープ、インラインコメントの考慮に対応する堅牢なパーサを実装。
    - PAPER_FILL_MODE/PAPER_TRADING_SQLITE_PATH 等の paper_trading 専用設定をサポート。

  - config_setup.py
    - 対話式 .env 設定ウィザードを追加。既存 .env の読み込み・編集、秘密項目のマスク表示、保存機能を提供。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）、本番環境に関するガードなどを実行。--strict モードで警告も失敗扱いに可能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 一貫したログ設定関数 setup_logging を実装。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定。
    - 既存ハンドラの二重設定回避（クリア → 再設定）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - stdout を用いることで cron 等からの出力リダイレクトの扱いを考慮。
  - utils/process_priority.py
    - プラットフォーム（Windows / POSIX 系）差異を吸収するプロセス優先度設定を実装。アクセス権限がない場合は警告を出して安全にスキップ。
    - CPU affinity 設定関数も提供（指定コア数に固定する）。

- ポートフォリオ構築関連（純粋関数群、副作用なし）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等ウェイト・スコア加重(w calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等分配へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用 (apply_sector_cap)。既存保有のセクター時価を計算して上限を超えるセクターの新規候補を除外。unknown セクターは上限適用外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、1銘柄上限・aggregate cap を考慮したスケーリング、cost_buffer による保守的見積り、残差分配ロジックを実装。

- リサーチ・ファクター
  - research/factor_research.py
    - Momentum などファクター計算モジュールの枠組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等を算出する設計。P95 計算などユーティリティを含む。
    - （注）ファイル末尾に実装途中の箇所が見られるため、いくつかの関数は現在開発中・未完の可能性あり。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。ペーパートレード DB（環境変数 PAPER_TRADING_SQLITE_PATH か --db オプション）を読み込み、稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を計算して PASS/FAIL を判定する。
    - デフォルトの合格基準値（稼働率 99%、Fill Rate 90%、Send Rate 95%、P95 レイテンシ 200ms）を定義。
    - DB に対象テーブルがない場合は安全に N/A を返す処理を持つ。

- パッケージ基本情報
  - __init__.py にバージョン "0.1.0" を設定。

### 変更 (Changed)
- ログ出力の扱いを明示的に stdout に統一（logging_setup）。cron/タスクランナーとの相性を考慮。

### 修正 (Fixed)
- 環境変数パースやポーリング間隔の不正値に対してフォールバック動作を実装（MONITOR_POLL_INTERVAL の警告 + デフォルト）。
- DB 接続やスレッド実行時に finally で確実に接続を close する等のリソース解放を追加。

### 注意点 / 既知の制約 (Known issues)
- research/factor_research.py の一部関数が途中で切れている（実装継続が必要）。
- position_sizing の一部注釈にあるように将来的な拡張（銘柄別 lot_size を外部マスタから取得など）の余地あり。
- process_priority で権限不足（psutil.AccessDenied）などが発生した場合は警告を出して処理をスキップする設計。実運用での挙動はプラットフォーム権限に依存。
- config の自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされる（CI/配布環境での挙動に注意）。

---

[0.1.0]: 0.1.0 - 2026-04-19
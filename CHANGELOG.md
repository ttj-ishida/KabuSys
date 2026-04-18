# CHANGELOG

このファイルは Keep a Changelog の形式に準拠します。  
このリリースノートは、与えられたコードベースの内容から推測して作成しています。

すべての変更履歴はリポジトリの現時点（v0.1.0）を反映しています。

## [Unreleased]
- 現時点の未リリース変更はありません。

## [0.1.0] - 2026-04-18
初回公開リリース（推測）。以下の主要機能・モジュールを実装しています。

### 追加
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッドでの engine.run_session 実行と停止フラグ（data/stop_requested.flag）による安全停止制御を実装。
    - 実行 PID ファイル path を管理（data/execution.pid、設定により変更可能）。
    - RiskConfig のデフォルト値（max_position_pct 等）を定義し、RiskManager に注入。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を一貫して利用）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt による終了処理あり。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み（.env, .env.local の順序、OS環境変数保護）。
    - 複雑な .env 構文解析対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants/Kabu API/DB パス/監視閾値/環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。

  - config_setup.py
    - 対話式設定ウィザード (.env の作成/更新)。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を定義しユーザ入力を誘導。
    - .env の読み込み・上書き・書き出しロジックを実装。

  - validate_config.py
    - 起動前検証 CLI。.env と config/*.yaml の設定不備を検出。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML が存在する場合は YAML ファイルのパース検証、本番環境向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）などを実施。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点時タイブレーク）、等金額配分、スコア正規化配分（全スコア 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中上限適用（既存保有のセクター比率が閾値を超える場合、新規候補を除外）を実装。unknown セクターは制限の対象外。
    - レジームに応じた資金乗数 calc_regime_multiplier（'bull'=1.0, 'neutral'=0.7, 'bear'=0.3、未知は 1.0 にフォールバック）を実装。

  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）考慮、cost_buffer（手数料・スリッページ補正）をサポート。
    - aggregate cap 超過時はスケーリングし、余りは fractional 残差に基づいて lot_size 単位で配分するロジックを実装。
    - price 欠損時のスキップ、コメントで将来的な改善案（前日終値等のフォールバック）を明記。

- 監視/分析関連
  - monitoring/monitoring_db.py（init_monitoring_db 呼び出しの利用により監視テーブル初期化を保証）
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等を集計。
    - 閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from/--to）、P95 計算、欠測テーブルに対する頑健な例外処理を実装。

- リサーチ
  - research/factor_research.py（ファクター計算モジュールの骨格）
    - Momentum, Value, Volatility, Liquidity の設計方針、定数定義、calc_momentum の骨組み（DuckDB 接続を受け prices_daily テーブル参照）を含む（ファイル末尾は断片的に含まれる）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一されたロギング設定ユーティリティ。stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの安全なクリア処理を実装。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値）、CPU affinity 固定機能を提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。

- パッケージ基礎
  - パッケージ初期化 src/kabusys/__init__.py で __version__ = "0.1.0" を設定、主要サブパッケージを __all__ に公開。

### 変更（実装上の注意点・挙動）
- .env 自動ロード順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- run_monitoring は監視 DB に常に sqlite_path（Settings.sqlite_path）を使用する設計（環境に依存しない監視データ収集）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使い、本番 DB とは分離する。
- logging_setup は stdout（stderr ではない）へ出力する設計。cron 等で stdout/stderr を一本化して扱いやすくしている。
- process_priority は権限不足 (psutil.AccessDenied など) 時に警告を出して処理を継続する安全設計。

### 修正（推測: 安全性・堅牢性向上）
- 環境変数パースの強化: export プレフィックス、クォート、エスケープ、インラインコメント処理を正確に扱うことで .env の柔軟性を向上。
- validate_config による起動前検証で設定ミスを早期に検出できるよう実装（本番事故防止）。
- DB 周りの初期化（init_monitoring_db）を起動時に保証し、テーブル未作成によるクラッシュを防止。

### 既知の制約・TODO（コード中の注釈より抽出）
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の注記。将来的に前日終値や取得原価などフォールバック価格を導入する予定。
- position_sizing:
  - 将来的に銘柄別 lot_size（単元株）マスタを導入し、銘柄ごとの単元対応を実装予定（現在は全銘柄共通 lot_size）。
- research/factor_research は calc_momentum 以降の実装が断片的（続き実装が必要）。

### セキュリティ
- .env は決して Git にコミットしない旨を config_setup の生成ファイルに明記している。

---

もし CHANGELOG に特定のフォーマットや追加項目（例: 変更理由、影響範囲、移行手順）を入れたい場合は、そのフォーマットに合わせて追記します。どの程度詳細に記載するか指示いただければ調整します。
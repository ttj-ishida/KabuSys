# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」規約に準拠します。  

注: 本CHANGELOGは提供されたコード内容から実装意図・機能追加を推測して作成しています。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-16

初回リリース。日本株自動売買フレームワークの以下主要コンポーネントを実装／追加しました。

### Added
- コア: パッケージ初期バージョンを定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行系
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine を起動するための初期化フローを実装。
    - プロセス優先度を最初に "high" に設定する仕組みを導入。
    - KABUSYS_ENV=paper_trading 時に専用の MockBrokerClient を使用し、paper_trading 用 SQLite DB（data/paper_trading.db、環境変数で上書き可）と完全分離して動作する。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。フラグ検知で安全停止。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み。
- 監視系
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様（監視データを本番 DB に収集）。
    - 停止フラグ（data/stop_requested.flag）検知でループ停止。
- 設定・環境変数管理
  - Settings クラス（src/kabusys/config.py）を実装。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサが export 構文、引用符、エスケープ、インラインコメント等に対応。
    - 必須環境変数取得ヘルパー _require。
    - 各種設定プロパティ: duckdb/sqlite のパス、PID/kill フラグパス、閾値（CPU/MEM/DISK）、KABUSYS_ENV 検証、LOG_LEVEL 検証、paper_trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）などを提供。
- ポートフォリオ構築（純関数群）
  - select_candidates / calc_equal_weights / calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）
  - apply_sector_cap / calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）
  - calc_position_sizes（src/kabusys/portfolio/position_sizing.py）
    - リスクベース、等分配、スコア加重などの配分方式に対応。
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer による保守的見積りと aggregate scaling を実装。
- 研究・因子計算
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200乖離等）
    - calc_volatility（ATR20, 相対ATR, 20日平均売買代金, 出来高比等）
    - calc_value（PER, ROE を raw_financials と結合して算出）
    - 全て DuckDB 接続を受け取り SQL で計算する実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（将来リターン算出、複数ホライズン対応）
    - calc_ic（Spearman ランク相関による IC 算出）
    - rank / factor_summary（ランク付け・統計サマリ）
  - research/__init__.py に公開 API を追加。
- ニュース NLP（AI）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）を追加（初期実装）。
    - 指定日のニュースウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する calc_news_window。
    - OpenAI（gpt-4o-mini）を用いたバッチスコアリング設計（バッチサイズ・リトライ・スコアクリップ・レスポンス検証・部分書き換えでの安全性を想定）。
    - API キー解決（api_key 引数または OPENAI_API_KEY 環境変数）。
- ユーティリティ
  - process_priority ユーティリティ（src/kabusys/utils/process_priority.py）
    - プラットフォーム差分を吸収してプロセス優先度を設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - 許可されない操作時は警告ログでフォールバックする堅牢設計。
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して標準出力にレポートを出力。
    - デフォルトの閾値（稼働率 99%、成功率 90% など）を設定。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

### Changed
- .env の自動読み込み順序と保護
  - OS 環境変数 > .env.local > .env の優先順位により自動ロード。既存 OS 環境変数は protected として .env/.env.local からの上書きを防止。
- DuckDB / SQLite の扱い
  - 監視系は常に本番 sqlite_path を参照する仕様に（監視データを一元化）。
  - 実行系は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離。

### Fixed
- 環境変数パースの堅牢化
  - _parse_env_line が export 先頭のサポート、引用符内のバックスラッシュエスケープ、インラインコメントの扱いを実装して不正な .env に対する誤動作を低減。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 以下や非数が指定された場合、警告ログを出してデフォルト値（60 秒）にフォールバックするように修正（run_monitoring）。
- ファクター/分析側の欠損値ハンドリング強化
  - 欠損・データ不足時に None を返す仕様、集計クエリがテーブル不在（OperationalError）でも安全に動作するフォールバックを tools/paper_verification_report に追加。

### Security
- 環境変数の扱い
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能（テスト時の意図しない読み込み防止）。
  - Settings._require による必須環境変数チェックで、シークレット未設定時に早期にエラーを出すようにして安全性を向上。

### Notes / Migration
- 実行前に以下を確認してください:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。
  - OPENAI_API_KEY が必要な機能（news_nlp）を利用する場合は設定してください。
  - data ディレクトリと必要な DB ファイル（data/monitoring.db, data/paper_trading.db 等）を作成しておいてください。
  - paper_trading モードを利用する場合は KABUSYS_ENV=paper_trading を設定して、PAPER_TRADING_SQLITE_PATH（任意）で DB を指定できます。
  - MONITOR_POLL_INTERVAL は正の整数を指定してください。不正値は 60 秒にフォールバックします。

---

今後の予定（例）
- news_nlp の API 呼び出し実装の完成（chunks の実装・結果書込処理の最終化）。
- Strategy / Execution の詳細ロジック（Engine 内部）・取引ログ連携のテスト充実。
- 単体テスト・統合テストの追加、および CI 設定。

（必要であれば、このCHANGELOGをさらに細分化してファイル名・関数単位での変更履歴を追記します。）
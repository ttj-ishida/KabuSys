# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

- リリースポリシー: 互換性のある変更は "Added / Changed / Fixed" に区分して記載します。  
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを実装しています。

### Added
- 基本パッケージ情報
  - パッケージメタデータ: kabusys.__version__ = "0.1.0"

- 設定・環境変数読み込み (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 複数のユーティリティ:
    - _parse_env_line: export 形式、クォート、インラインコメント等を考慮した .env パース。
    - _load_env_file: OS 環境変数の保護（protected）を考慮した上書き挙動。
  - Settings クラス: 各種設定プロパティを提供（検証付き）。
    - J-Quants / kabu API / LINE API トークン類、DB パス（duckdb/sqlite/paper_trading）、
      PID/kill フラグパス、監視閾値（CPU/Memory/Disk）、ログレベル、環境種別判定（development/paper_trading/live）など。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - 環境値が未設定の場合の明示的なエラー (_require)。

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に分離して実行（settings.paper_sqlite_path / data/paper_trading.db がデフォルト）。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動制御（スレッド実行、停止フラグ監視）。
    - デフォルトでプロセス優先度を "high" に設定。
    - risk のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）を指定。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグファイル (data/stop_requested.flag) の検知でループ終了。
    - 監視でもプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を用いた監視テーブル存在保証（冪等処理）。

- 純粋関数ベースのポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: スコア降順・タイブレークルール付き候補選定（max_positions）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（全銘柄スコア0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベース算出、sell_codes を除外可能）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（既定値: bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method="risk_based" | "equal" | "score" をサポート。lot_size（単元）処理、stop_loss/risk_pct ベースのリスク算出、per-position 上限・aggregate cap（available_cash）でスケーリング、cost_buffer による保守的見積り、残余での端数処理などを実装。

- 研究・ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（不足データ時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率（データ不足は None）。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials の最新報告を target_date 以前で取得）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（ホライズン検証あり）。
    - calc_ic / rank: スピアマンランク相関（IC）の計算、ランク化ユーティリティ（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median の統計要約（None 値除外）。
  - DuckDB を利用した SQL+Python の組合せで設計（prices_daily / raw_financials 参照前提）。

- ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの実装（高レベル設計、堅牢なリトライ・バッチング設計）。
  - 主な特徴:
    - タイムウィンドウ計算（JST 翌日 08:30 などの UTC 変換ロジック）calc_news_window。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、スコアクリップ（±1.0）。
    - API キー解決と入力バリデーション、部分成功時に既存スコア保護するための安全な DB 書換戦略（DELETE→INSERT の部分的適用）。
  - （注）ファイルは大枠の実装を含むが、リポジトリ内では処理の続きがあるため、実行前に API キーやテーブル構成を確認してください。

- ツール類 (kabusys.tools)
  - paper_verification_report.py: Paper Trading の検証レポート生成 CLI。
    - レポート指標: 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - 判定基準（デフォルト閾値）を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ (--from/--to)、DB 指定 (--db) 対応。PAPER_TRADING_SQLITE_PATH を優先。

- プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収する実装。アクセス権限や未実装 API に対するフォールバック警告あり。
  - set_cpu_affinity(cpu_count): 指定コア数へのピンニング。検証とエラーハンドリングを実装。

- DB 関連
  - sqlite3 + duckdb を併用する設計（ロギング/監視は SQLite、分析は DuckDB 想定）。
  - monitoring 用テーブルを初期化する init_monitoring_db を参照する箇所を各起動スクリプトで呼び出し、テーブル存在を保証。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注意事項 / 運用メモ:
- paper_trading 環境は本番 DB と完全に分離する設計です（PAPER_TRADING_SQLITE_PATH / settings.is_paper により制御）。
- run_monitoring / run_execution はプロセス優先度を最初に "high" に設定しますが、権限不足等で設定に失敗する場合は警告を出して継続します。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後は必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して制御してください。
- OpenAI を用いる機能は外部 API キーと料金が発生するため、本番運用時は注意して設定してください。

（以降のリリースでは互換性やバグ修正、機能追加をカテゴリ別に追記します。）
CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし（開発中の変更はここに記載してください）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys (version 0.1.0)
  - コア実行スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
      - 監視処理は本番用の sqlite_path を環境にかかわらず使用。
      - sqlite (SQLite3) と DuckDB へ接続して監視 DB を初期化。
      - monitor.check_once() で発生した例外はログに記録して継続するフェイルセーフ実装。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH で上書き可能）。
      - paper_trading 時は BrokerClientFactory により MockBrokerClient を利用する設計（実運用のブローカー分離対応）。
      - デーモンスレッドでエンジンを実行、停止フラグ検知で安全に停止。
      - エンジン用 PID ファイル管理（data/execution.pid）。
  - 設定管理
    - config.Settings クラスを実装。
      - .env 自動ロード（プロジェクトルートに .env / .env.local があれば読み込む。OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - export KEY=val、クォートやエスケープ、インラインコメントなどを考慮した堅牢な .env パーサを実装。
      - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
      - データベース・監視・システム設定用プロパティ（duckdb_path、sqlite_path、paper_sqlite_path、pid_file_path、閾値等）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: スコア降順で候補選定、同点は signal_rank でタイブレーク。
      - calc_equal_weights / calc_score_weights: 重み算出（score の合計が 0 の場合は等分配にフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（売却予定コード除外、"unknown" セクターは制約を適用しない）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知は警告して 1.0 にフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積り、残差再配分アルゴリズムを実装。
      - 将来拡張用に個別 lot_size をサポートする TODO を明記。
  - リサーチ機能（DuckDB ベース）
    - research.factor_research
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
      - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率等。
      - calc_value: PER / ROE（raw_financials と prices_daily を組み合わせ）。
      - いずれも DuckDB 接続を受け取り SQL で効率的に計算。外部ライブラリに依存しない設計。
    - research.feature_exploration
      - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（horizons の検証あり）。
      - calc_ic: スピアマンのランク相関（IC）計算（欠損・同順位処理対応）。有効レコードが少ない場合は None を返す。
      - factor_summary / rank: 基本統計量とランク変換ユーティリティを実装。
    - research.__init__ エクスポートで zscore_normalize などを公開。
  - ニュース NLP（AI）機能
    - ai.news_nlp モジュールを追加（ニュース記事を OpenAI API でセンチメント解析して ai_scores に書き込む想定）。
    - 概要: タイムウィンドウ集約、銘柄ごとのトリム、20 銘柄単位のバッチ送信、429/ネットワーク/5xx で指数バックオフ、レスポンス検証、スコア ±1.0 にクリップ、部分的な更新保護（対象コードで DELETE→INSERT）等を設計。
    - 使用モデルは gpt-4o-mini、JSON モードを想定。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率・注文成功率・送信率・P95 レイテンシなどを計算し、閾値と突き合わせて PASS/FAIL を出力。
      - P95 計算、各種 SQL クエリ、期間フィルタの実装。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority(level): Windows / POSIX の差異を吸収して優先度を設定（失敗時は警告してスキップ）。
      - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を設定（失敗時は警告してスキップ）。
  - パッケージメタ情報
    - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- なし（初回リリース）

Fixed
- run_monitoring / run_execution の起動シーケンスでプロセス優先度を起動直後に設定するように整理し、優先度設定の失敗を非致命的に扱うことで起動の堅牢性を向上。

Security
- なし

Removed
- なし

Known issues / Notes
- ai/news_nlp.py は設計が整っており多くの堅牢化を盛り込んでいますが、今回のソーススナップショットはファイル末尾が途中で切れており（"if not articl" で中断）、そのままではインポート時に SyntaxError になる可能性があります。OpenAI API キー未設定時の ValueError を用意する等の安全策は実装されていますが、動作確認・マージ前にファイルの補完が必要です。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過少見積もられる旨の TODO を記載。将来的には前日終値や取得原価によるフォールバックを検討。
- position_sizing: lot_size を全銘柄共通としているため、将来的に銘柄別単元対応が必要（TODO 記載）。
- .env パーサは多くのケースを扱うが、極端に複雑な .env のエッジケースは要確認（自動ロードを無効化するフラグあり）。

移行手順 / 使用メモ
- 環境変数の自動ロード:
  - デフォルトでプロジェクトルートの .env を読み、.env.local を上書き読み込みします。
  - OS 環境変数は上書きされません（protected）。
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると、paper_trading 用の SQLite DB（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH などで挙動を調整できます。
- 実行:
  - 監視は python -m kabusys.run_monitoring を想定（MONITOR_POLL_INTERVAL で間隔調整）。
  - エンジン起動は python -m kabusys.run_execution を想定（停止は data/stop_requested.flag）。

今後の改善候補
- ai/news_nlp の完成およびエンドツーエンドテストの追加。
- ポートフォリオ構築の単元株・銘柄別 lot_size 対応。
- apply_sector_cap の価格フォールバック実装。
- DuckDB クエリのパフォーマンステストおよび大口データ用の最適化。
- 単体テスト・統合テストの整備（特に金融計算ロジック、リスク/発注関連）。

---
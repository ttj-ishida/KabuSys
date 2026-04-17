# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" 準拠です。  

なお、本ログはソースコードの内容から推測して作成しています。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys パッケージ（__version__ = 0.1.0）。
- 環境/設定管理
  - Settings クラスを備えた設定モジュールを追加（src/kabusys/config.py）。.env / .env.local の自動読み込み（OS 環境変数を保護する仕組みあり）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - .env ファイルパーサの強化：export 式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理の改善。
  - 各種環境変数とデフォルト値を定義（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
  - PAPER_FILL_MODE のバリデーション（有効値: instant | partial | never | reject）。

- 実行 / 監視用スクリプト
  - 実行エンジン起動スクリプト run_execution を追加（src/kabusys/run_execution.py）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - paper_trading 環境では paper_trading 用 SQLite（data/paper_trading.db のデフォルト）を使用し、本番 DB と分離。
    - RiskManager, OrderManager, Reconciler, ExecutionEngine の組み立てと起動ロジック（PID ファイル管理、停止フラグ監視、デーモンスレッドでの実行）。
    - RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）し、初期ポートフォリオ値は broker.get_available_cash() を参照。

  - 監視ポーリングループ起動スクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記（監視データの一元化）。
    - 停止フラグファイルにより外部からループを終了可能。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 / signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等配分とスコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限チェック（unknown セクターは除外対象にならない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームはフォールバックで 1.0、警告ログ）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method による株数決定（risk_based / equal / score）。ロット丸め（lot_size）対応、単銘柄上限・aggregate cap の実装、cost_buffer を用いた保守的コスト見積り、スケーリングと残差配分ロジック実装。

- リサーチ / 特徴量計算
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value：DuckDB 上の prices_daily / raw_financials を参照して各種ファクター（リターン、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - スキャン窓や必要なデータ行数不足時の None ハンドリングを実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns：複数ホライズンの将来リターンを一括取得（horizons の検証あり）。
    - calc_ic：スピアマンのランク相関（IC）実装（同順位は平均ランクで処理）。有効レコード数が不足する場合は None を返す。
    - rank / factor_summary：ランク変換と基本統計量計算（count/mean/std/min/max/median）。

- AI ニュース NLP（OpenAI 統合）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ（最大 20 銘柄）で送信して銘柄別センチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - JSON モードへの依存・レスポンス検証、スコアを ±1.0 にクリップ、429/ネットワーク/5xx のエクスポネンシャルバックオフによるリトライ（上限あり）。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）と記事トリミング（最大記事数・最大文字数）実装。
    - API キー未設定時に明示的な例外を送出。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。権限不足等は警告ログでフォールバック。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能（引数検証・権限不足時の警告対応）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを算出して標準出力へ整形。
    - コマンドライン引数 (--from / --to / --db) と PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
    - SQL エラー（テーブル未存在など）に対する耐性（例外時は N/A / 0 として扱う）。

- DB 接続
  - DuckDB をリサーチ / AI 処理用に使用（duckdb 接続を引数で受ける設計）。
  - monitoring 用 sqlite 初期化関数取り込み（init_monitoring_db を使用して冪等にテーブルを保証）。

### Changed
- 設定読み込みの挙動を明確化
  - .env と .env.local の読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は上書きモード）。OS 環境変数は protected として上書きされない。

### Fixed / Hardened
- MONITOR_POLL_INTERVAL の不正値対策（非正整数・文字列等）：警告ログを出してデフォルト 60 秒にフォールバック（run_monitoring）。
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし、WARNING を出力。
- DuckDB executemany の制約回避（ai/news_nlp 内 コメントに記載）：空 params を渡さないガードを用意する設計。

### Notes / Known limitations
- position_sizing:
  - lot_size は現状全銘柄で共通（デフォルト 100）。将来は銘柄別 lot_size をサポートする設計に拡張予定（TODO コメントあり）。
  - apply_sector_cap のエクスポージャー計算では price が欠損（0.0）の場合に過少評価となりブロックが外れる可能性があり、将来的なフォールバック価格導入を検討中。

- news_nlp:
  - OpenAI API を利用するため API キーが必須（引数または環境変数 OPENAI_API_KEY）。API 利用に伴うコスト・レート制限の考慮が必要。
  - 実装は API 失敗時にスキップして継続するフェイルセーフ設計だが、部分失敗時のテーブル更新戦略（該当コードのみ置換）は意図的に採用しているため、完全性の保証は環境依存。

- 時刻処理:
  - ニュース集約等で使用するタイムウィンドウ計算はルックアヘッド防止のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。

### Security
- 環境変数の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数は保護され上書きされない仕組み。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時にはコミットログやリリース方針に基づく調整を推奨します。）
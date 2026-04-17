Keep a Changelogに準拠した CHANGELOG.md（日本語）

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に従い、重要な変更を記録します。

フォーマット:
- 構成: Unreleased / [version] - YYYY-MM-DD
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security, その他（Notes / Known issues）

Unreleased
- なし

[0.1.0] - 2026-04-17
Added
- 全体
  - 初回リリース (v0.1.0)。パッケージ名: kabusys（__version__ = "0.1.0"）。

- 設定・環境読み込み (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数経由でアプリ設定を一元管理。
  - 自動 .env ロード機能を追加:
    - プロジェクトルートを .git / pyproject.toml から探索して .env, .env.local を自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - OS 環境変数は保護され、.env.local の override オプションを採用。
  - .env パーサを強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 各種設定値の検証を実装:
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、PAPER_FILL_MODE（instant/partial/never/reject）などのバリデーション。
  - DB パス関連プロパティ:
    - duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path 等を提供。

- 実行/監視エントリポイント
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB から分離（MockBrokerClient を利用する想定）。
    - 起動前に停止フラグ (data/stop_requested.flag) をチェックし、安全に起動/停止する仕組みを実装。
    - エンジンの PID ファイル管理（data/execution.pid）とスレッドでの実行・監視ループを実装。
    - デフォルトでプロセス優先度を "high" に設定する処理を呼び出す。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を定期実行するポーリングループを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用して status を記録する設計。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクリーンアップを実装。
    - プロセス優先度設定を起動直後に行う（set_process_priority）。

- モニタリング DB 初期化
  - init_monitoring_db を呼んで監視用テーブルが存在することを保証（冪等な初期化）。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 向け検証レポート生成ツールを追加。
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下件数、レイテンシ（avg/max/P95）などを集計して標準出力に整形レポートを出力。
    - PASS/FAIL 判定基準（しきい値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ポートフォリオ構築関連 (src/kabusys/portfolio/)
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点時 signal_rank 昇順）で選別。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限(max_sector_pct) を評価し、上限超過セクターの新規候補を除外。売却予定銘柄（sell_codes）をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を実装（未知レジームは 1.0 フォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算を実装。
    - 単元株( lot_size ) で丸め、1 銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的コスト見積り、端数の再配分ロジックを実装。
    - risk_based 方式では stop_loss_pct と risk_pct に基づく目標株数算出。
    - 一部の欠損価格処理について将来のフォールバック対応の TODO 記載。

- リサーチ / ファクター (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB 上で SQL 実行）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS が 0/欠損の際は None）。
  - feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコード 3 未満は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは zscore_normalize をエクスポートして分析ワークフローを支援。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリングモジュールを追加。
    - タイムウィンドウ計算 calc_news_window（JST 基準の前日 15:00 ～ 当日 08:30 の UTC 変換）を提供。
    - score_news 関数は DuckDB の raw_news / news_symbols / ai_scores テーブルから記事を集約し、最大 20 銘柄/バッチで OpenAI に送信、429/5xx/ネットワーク断に対して指数バックオフのリトライを行う設計。
    - スコアは ±1.0 にクリップ、レスポンスのバリデーションと部分置換（DELETE→INSERT）で DB 書き換えを行う方針を記載。
    - OPENAI_API_KEY 環境変数または api_key 引数で API キーを解決するよう実装。
  - 注意: 大量テキスト/トークン肥大化対策のため、1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を設けている。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level)、set_cpu_affinity(cpu_count) を実装。
    - Windows と POSIX 系の差分を吸収（psutil を使用）。アクセス拒否や未実装 API を考慮して警告を出してスキップする堅牢性を確保。

- DB/分析基盤
  - runtime には sqlite（monitoring.db / paper_trading.db）を使用、分析・リサーチには DuckDB を使用する方針を反映（duckdb_path 設定）。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL の入力妥当性検査を追加。不正な値は警告してデフォルト 60 秒にフォールバック。

Notes / Known issues / TODO
- ai/news_nlp.py の実装は概ね完成方針を示しているが、リポジトリ内のスニペットでは後段（記事フェッチ関数 _fetch_articles の実装など）が途中で切れている箇所が見受けられます。実運用前に以下を確認／完了してください:
  - _fetch_articles の実装（raw_news からの集約ロジック）。
  - OpenAI API 呼び出し周りの実行/リトライ/エラー処理のエンドツーエンド検証。
  - DuckDB 側の ai_scores 置換処理（部分失敗時の保護ロジック）の検証。
- position_sizing, risk_adjustment のコード中にある TODO:
  - 価格欠損時のフォールバック（前日終値や取得原価の利用）を将来的に検討する旨が記載されています。
  - 現状 lot_size は全銘柄共通と仮定。将来、銘柄別 lot_map への拡張を想定。
- プラットフォーム依存:
  - process_priority / cpu_affinity は psutil の実行権限に依存するため、環境によっては設定が無視される可能性があります（警告ログが出力される）。

Security
- なし（公開されているコード断片から重大なセキュリティ修正は検出されていません）。OpenAI API キー等の機密情報は環境変数で提供する設計になっているため、運用時は環境変数管理に注意してください。

References / Migration notes
- .env 自動ロードの挙動変更に注意:
  - OS 環境変数が優先され、.env.local は OS 環境変数以外を上書きできます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は明確に分離されています:
  - 実行エンジンは paper_trading 環境時に data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）を使用します。
  - 監視（monitoring）は環境に依らず sqlite_path（デフォルト data/monitoring.db）を使用する設計です。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や issue/PR の記録がある場合は、それらに基づいて補完・修正してください。）
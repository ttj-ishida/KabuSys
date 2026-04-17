CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

記載ポリシー:
- ここに記載するのはコードベース（src/ 以下）の実装に基づき推測してまとめたリリースノートです。
- 実装中の TODO や未実装・部分実装の箇所についても「既知の問題」として明記します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初期実装: kabusys (version 0.1.0)
  - パッケージエントリで __version__ = "0.1.0" を定義。
- 実行・監視用の起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB (data/paper_trading.db、環境変数で上書き可) を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアントの生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立ててエンジンをスレッドで起動。
    - data/stop_requested.flag の存在を確認して安全に停止する仕組みを提供。起動時に停止フラグが既にあれば起動を中止。
    - 実行中は data/execution.pid を PID ファイルとして扱う想定（設定経由で変更可）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照して監視 DB を扱う実装。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 環境設定ユーティリティ
  - config.py
    - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト用途）。
    - .env のパース実装（コメントやクォート、エスケープを考慮）。
    - Settings クラスを提供し、各種環境変数をプロパティとして安全に取得（必須項目は _require で ValueError を投げる）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path, duckdb_path, sqlite_path 等の Path 型プロパティを提供。
    - 監視関連の閾値プロパティ（CPU/MEM/DISK など）や PID / kill flag 関連設定を提供。
- ポートフォリオ構築モジュール（純粋関数群、DB参照無し）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 重み計算。全スコアが 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用して候補銘柄をフィルタリング（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数を返す（bull/neutral/bear、未知は 1.0 として警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算、単元株（lot_size）単位丸め、per-position 上限・aggregate cap（スケールダウン）を実装。
    - cost_buffer を考慮した保守的見積り、残差処理で lot 単位の追加配分ロジック付き。
    - 将来拡張の TODO（銘柄別 lot_size マップの導入）を注記。
  - portfolio/__init__.py から必要関数を公開。
- 研究・リサーチ用モジュール（DuckDB を使用）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials と prices_daily から PER/ROE 等を計算（最新財務レコードの取得ロジック含む）。
    - DuckDB SQL ベースで高速に集計する設計。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（horizons のバリデーションあり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（データ不足時は None）。
    - factor_summary, rank: ファクター統計とランク化ユーティリティを実装。
  - research/__init__.py で zscore_normalize（data.stats から）と主要 API をエクスポート。
- AI ニュース NLP スコアリング（OpenAI 利用）
  - ai.news_nlp
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとにセンチメントスコア（-1.0〜1.0）を ai_scores テーブルに書き込む設計。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、リトライ／バックオフ、レスポンスバリデーション、結果クリップなどの堅牢化ロジックあり。
    - calc_news_window により JST ベースのニュースウィンドウを UTC naive datetime で計算するユーティリティを提供。
    - API キー解決（引数 or OPENAI_API_KEY）とキー未設定時の ValueError。
- CLI ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポートを SQLite DB（デフォルト: data/paper_trading.db）から生成する CLI ツールを追加。
    - レポートは稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を出力。
    - パスフィルタ（--from / --to / --db）対応、閾値（稼働率 99%、Fill 90% 等）と PASS/FAIL 判定を実装。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows/Linux（およびサポート POSIX）でプロセス優先度を抽象化して設定。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスをピン留め（引数 None だと何もしない）。権限不足時に警告してスキップ。

Changed
- （初版）内部設計メモ・仕様がソース内コメントとして多数追加されており、実装意図が明示化されている（PortfolioConstruction.md / StrategyModel.md への参照等）。

Fixed
- （該当なし：初版リリース）

Security
- OpenAI API キーなど機密値は Settings/_require や引数で参照し、未設定時は明示的にエラーを出すことで不正な実行を防止する実装。

Known issues / Notes
- ai/news_nlp.py がソース末尾で途中（トランケート）になっている箇所を検出：
  - ファイル末尾で score_news の内部処理が途中で切れており（最後に "if not articl" で終わっている）、記事集約→API呼び出し→DB書き込みまでの処理が完全には表示されていません。実運用前にこの関数の残り実装を確認・完成させる必要があります。
- apply_sector_cap の価格欠損時の挙動に関する TODO:
  - price が欠損（0.0）だとエクスポージャーが過少見積りされ、ブロックが外れてしまう旨の注意書きあり。将来的には前日終値や取得原価でのフォールバックを検討すると良い。
- position_sizing の lot_size 周りの拡張未実装:
  - 将来的に銘柄別 lot_map を受け取る設計拡張の TODO が残る。
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」設計になっている点に注意:
  - テストや paper_trading で監視データを分離したい場合は実装を変更する必要がある。
- config の .env ローダはプロジェクトルートの自動検出に依存する:
  - 配布形態やインストール後の環境では .git / pyproject.toml が存在しない場合、自動読み込みをスキップする（意図的）。
- DuckDB を使う研究モジュールは prices_daily / raw_financials 等のスキーマ依存:
  - DB スキーマが一致しないとクエリ実行時に sqlite3.OperationalError / duckdb エラーが発生する可能性がある。
- エラーハンドリング方針:
  - 多くの起動スクリプト・ツールは fail-safe 的に警告ログを残して継続する設計（例: プロセス優先度設定失敗時や API 呼び出し失敗時のリトライ/スキップ）。

Developers
- 実装に関する補足コメント・設計意図（PortfolioConstruction.md, StrategyModel.md 等）をソース内に残しています。将来の拡張や運用ルールはこれらの注釈を参考にしてください。

--- 

（この CHANGELOG はソースコードから推測して作成したものです。実際のコミット履歴やバージョン運用ルールに合わせて適宜編集してください。）
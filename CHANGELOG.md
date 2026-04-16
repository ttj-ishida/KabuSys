CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。本ファイルは Keep a Changelog の慣例に準拠しています（カテゴリ: Added / Changed / Fixed / Security）。  
各エントリは、コードベースから推測される機能追加・改善・修正を日本語でまとめたものです。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-16
-----------------
初回リリース。以下の主要機能群と設計方針を実装しています。

Added
- 基本構成
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - Settings クラスを追加し、環境変数 / .env / .env.local からの設定読み込みを提供。
    - 自動ロードはプロジェクトルート検出 (.git または pyproject.toml) に基づく。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
    - .env と .env.local の読み込み順序、OS 環境変数の保護（protected）に対応。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を利用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッドでの実行制御、停止フラグ（data/stop_requested.flag）検出による安全停止。
    - 実行 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは常に実運用 DB に蓄積）。
    - 停止フラグ検知による安全終了、check_once() の例外耐性で次ポーリングへ継続。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを実行前に行うことで監視用テーブル存在を保証（冪等）。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - コマンドライン引数 --from/--to/--db に対応。
    - 稼働率、注文成立率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定。
    - デフォルト DB は data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
    - P95 計算、各種 N/A ハンドリング、しきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。

- ポートフォリオ構築モジュール
  - kabusys.portfolio:
    - portfolio_builder: 候補選定（スコア降順、タイブレークに signal_rank）、等金額・スコア加重の重み計算。
    - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め（lot_size）、aggregate cap によるスケールダウンと残差処理。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - 設計は純粋関数（DB 参照なし）かつ PortfolioConstruction.md / StrategyModel.md に基づく想定アルゴリズム実装。

- リサーチ（ファクター計算・特徴量探索）
  - kabusys.research:
    - factor_research: Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、出来高）および Value（PER/ROE）計算関数を DuckDB クエリで実装。
    - feature_exploration: 将来リターン計算（fwd 1/5/21 日等）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク変換のユーティリティを実装。
    - 設計方針として DuckDB 接続を受け取り、標準ライブラリのみで完結する実装。

- AI ニュース NLP スコアリング
  - kabusys.ai.news_nlp: raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを算出して ai_scores へ保存する処理を実装。
    - タイムウィンドウ（JST 基準）計算ユーティリティ calc_news_window。
    - バッチ処理（最大 20 銘柄 / API コール）、1銘柄あたりの文字数・記事数上限、リトライ（429/5xx/ネットワーク系）用の指数バックオフ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗に強い DB 書き込み戦略（対象コードの絞り込み）を設計。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定（Windows / POSIX の差分吸収）、CPU affinity 設定ユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

Changed
- .env パーサの機能強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での振る舞い差分）を実装。
  - 不正な行や空行を無視する堅牢な実装。

- Settings のバリデーション強化
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）と不正値時の例外。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値集合）。
  - 各種閾値・パス設定にデフォルト値を用意（duckdb/sqlite/paper_sqlite/pid_path 等）。

- ポートフォリオ・サイズ計算のスケーリング改善
  - aggregate cap 超過時にスケールダウンし、lot_size 単位で残余を再配分するロジックを導入して再現性のある配分を行うよう改善。

- 監視 / 実行スクリプトの堅牢化
  - モニタリングのポーリング間隔取得処理で不正値を検知してデフォルトへフォールバック（警告ログ）。
  - check_once() 実行中の例外をキャッチしてループ継続するフェイルセーフ。

Fixed
- process_priority の例外処理追加
  - psutil のアクセス権限不足や未実装例外を捕捉し警告を出すことで起動失敗を回避。

- 各種 NULL/欠損ハンドリング
  - research の SQL クエリや集計でデータ不足時に None を返す設計にし、上位で N/A 表示やスキップ処理が可能に。
  - paper_verification_report の各クエリ呼び出しで sqlite3.OperationalError を捕捉してレポート生成を続行。

- rank / calc_ic の数値安定性向上
  - ランク計算前に round(..., 12) による丸めを導入し、浮動小数の丸め誤差による ties 検出漏れを防止。
  - 有効レコード数が不足する場合は None を返して無効扱いにする。

Security
- OpenAI API キー取り扱い
  - news_nlp.score_news は API キーが未設定の場合に ValueError を投げ、安全に処理を中断するように明示。

Notes / Design decisions
- Paper Trading と Live（本番）は DB を明確に分離して扱う設計（paper_trading 用 SQLite を用意）。
- モニタリングは運用上重要なデータを常に本番側に集約する方針を取っている（run_monitoring は本番 sqlite_path を使用）。
- 戻り値や集計値が存在しない場合は None / "N/A" を返す一貫したポリシーを採用。これによりレポートや上位ロジックは欠損を明示的に扱える。
- DuckDB を分析用 DB として利用し、ファクター計算 / リサーチ処理は DuckDB 上の prices_daily / raw_financials を参照する方針。

今後の改善候補（コード中の TODO 等から推測）
- position_sizing の銘柄別 lot_size 対応（stocks マスタから lot_size を取得する拡張）。
- apply_sector_cap における price 欠損時のフォールバック価格（前日終値や取得原価など）導入。
- news_nlp のリトライロジックや partial-failure 時のより粒度の高い保護（トランザクション／部分コミットの改善）。
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）の正式同梱と API リファレンスの充実。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートやバージョン履歴は開発・運用チームの記録に基づいて補完してください。）
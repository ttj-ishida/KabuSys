# CHANGELOG

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。以下は、与えられたコードベースの内容から推測・要約して作成した変更履歴です。

注: 本ファイルはコードから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。

## [Unreleased]

### Added
- 起動スクリプトを追加/整備
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を監視してグレースフルに終了。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用して接続。DuckDB 連携あり。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine のスレッド実行と停止フラグによる停止制御を実装。
    - 実行用 PID ファイル（data/execution.pid）管理。

- 設定管理を強化（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートの検出に .git / pyproject.toml を使用）。
  - OS 環境変数を保護するための上書き制御（.env.local は上書き、ただし既存 OS 環境変数は保護）。
  - .env パーサーを強化（export 句対応、シングル/ダブルクォート内のバックスラッシュエスケープ・インラインコメント処理、コメント処理の挙動調整）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを提供し、各種設定値（J-Quants / kabu API / LINE / DB パス / 監視閾値 / env のバリデーション等）をプロパティで取得可能に。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
  - KABUSYS_ENV / LOG_LEVEL の有効値チェックを追加。

- 監視・検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を読み、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを集計して CLI で報告するコマンドラインツールを追加。
    - --from / --to / --db オプションをサポート。
    - パスやテーブル欠損時のフォールトトレランス（OperationalError のハンドリング）を実装。
    - 判定基準（稼働率・成功率・送信率・P95 レイテンシ）の閾値を定義して PASS/FAIL を出力。

- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコア 0 の場合は等分配にフォールバックし WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価評価に基づく）。sell_codes を考慮して当日売却予定は除外可能。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 でフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定を実装。
    - リスクベース計算、lot_size（単元）丸め、max_position_pct による per-stock 上限、available_cash に対する aggregate cap のスケールダウンアルゴリズム（cost_buffer を考慮）。
    - スケーリング後の端数処理として、fractional remainder に基づき残余キャッシュで lot 単位を順次配分する仕組みを実装。

- 研究・リサーチ機能を追加（kabusys.research）
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily/raw_financials を参照して各種ファクター（モメンタム・MA200乖離・ATR・売買代金・PER/ROE 等）を計算。
    - 長期移動平均やウィンドウサイズ等は定数化し、データ不足時は None を返す設計。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合、None 除外、最小データ数チェック）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - research/__init__.py で上記 API を公開（zscore_normalize を含む）。

- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を使ったニュースセンチメントスコアリングの初期実装を追加。
  - 処理方針:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で記事を集約。
    - 銘柄ごとに記事数・文字数の上限を設定してトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズでまとめて API コール、429/ネットワーク/5xx 等は指数バックオフでリトライ。
    - 出力は厳密な JSON（{"results":[{"code":"XXXX","score":0.0},...]}）を期待し、レスポンス検証・スコアクリッピング（±1.0）を実施。
    - API キー未設定時は ValueError を送出。
    - 処理が途中失敗しても他銘柄の既存スコアを保護するため、対象コードで部分的に DELETE→INSERT する戦略を採用（DuckDB の executemany 制約に配慮）。

- ユーティリティを追加/改善（kabusys.utils）
  - process_priority.py
    - set_process_priority(level) を追加し、Windows / POSIX（Linux, Darwin, FreeBSD）で優先度を抽象化して設定。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピンニング可能。
    - アクセス権限不足や未対応環境では警告を出して安全にスキップ。
  - 各パッケージの __init__.py を整備して公開 API を整理。

### Changed
- DB の使用ポリシーを明示化
  - 監視(run_monitoring) は環境にかかわらず本番 sqlite_path を使用する設計になっている（意図的な分離ポリシー）。
  - 実行(run_execution) は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全に分離。
- .env 読み込み順序調整
  - 読み込み優先度を OS 環境変数 > .env.local > .env とし、.env.local は上書き可能だが OS 環境変数は保護する方式に変更。
- 設定値のバリデーション強化
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL などの不正値に対する ValueError を導入。
- ログ出力や例外ハンドリングの改善
  - 起動時に KABUSYS_ENV をログ出力。
  - ポーリングループ内で monitor.check_once() が例外を投げてもループ継続（例外ログを残して次回ポーリングを待機）。
  - process_priority の失敗時に詳細な警告ログを出すように変更。

### Fixed
- MONITOR_POLL_INTERVAL の取り扱いで不正な値（0 以下や非整数）を指定した場合にデフォルトへフォールバックして ValueError を回避するよう修正。
- calc_score_weights: 全スコア合計が 0 の場合は等金額配分へフォールバックし警告を出すように修正（ゼロ除算回避）。
- position_sizing のスケーリング処理で lot_size 単位の丸めと残差配分を行い、合計コストが available_cash を超えないように調整するロジックを導入（過投資防止）。
- process_priority / set_cpu_affinity: 権限不足や未サポート OS での例外を捕捉して WARN を出すようにして、クラッシュしないよう堅牢性を向上。

### Security
- ai/news_nlp.score_news は OpenAI API キー未設定時に明示的に ValueError を発生させるようにし、API キーの存在チェックを強化。

### Removed
- 該当なし（コードベースからは削除を示唆する痕跡は確認できませんでした）。

---

## [0.1.0] - Initial release
- パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 基本的なパッケージ構成（data/strategy/execution/monitoring/portfolio/research/ai 等のモジュール群）を導入。
- コア機能:
  - ExecutionEngine / Order 管理 / RiskManager / Reconciler の枠組み（run_execution 起動フロー）。
  - SystemMonitor と監視用 DB 初期化（init_monitoring_db）。
  - ポートフォリオ構築およびポジションサイズ計算の基礎実装。
  - DuckDB を使ったリサーチ系のファクター計算（モメンタム/ボラティリティ/バリュー/将来リターン/IC/統計サマリー）。
  - 簡易的な .env ローダーと Settings 抽象化。

(注) 実際の「初期リリース日」や過去の変更履歴はソース管理のコミット履歴を参照してください。本 CHANGELOG は提示されたコードの構造・コメント・実装から推測して作成した要約です。必要があれば、各項目をさらに細分化してコミット単位の変更点へ落とし込むことも可能です。
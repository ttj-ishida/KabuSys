CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
可能な限りソースコードから意図を推測してまとめています（実際のコミット履歴と差異がある場合があります）。

Unreleased
----------

- ドキュメントやロギングの微調整・内部実装の堅牢化
  - 環境変数のパースやデータベース初期化処理でのエラーハンドリングを強化。
  - モニタリング / 実行エンジン起動時のプロセス優先度設定と停止フラグ監視処理の安定化。

[0.1.0] - 2026-04-16
--------------------

Added
- パッケージ初期実装 (kabusys v0.1.0)
  - 全体説明を含むパッケージメタ情報を追加（src/kabusys/__init__.py）。
- 実行エンジン起動スクリプト
  - run_execution.py を実装。ExecutionEngine の起動、スレッド管理、停止フラグ監視を行う。
  - KABUSYS_ENV=paper_trading モード時は専用の paper_trading DB (data/paper_trading.db デフォルト) を使用し、本番 DB と分離する設計を導入。
  - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て例を実装。RiskConfig のデフォルト値（max_position_pct 等）を定義。
- 監視ポーリング起動スクリプト
  - run_monitoring.py を実装。SystemMonitor の初期化、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き、停止フラグによる終了をサポート。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
- 設定管理モジュール
  - config.py に Settings クラスを実装。環境変数の取得・検証ロジックを提供。
  - .env 自動ロード機能を実装（.env / .env.local、OS 環境変数を保護する protected 処理）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 各種設定プロパティを追加（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等）。PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
- ポートフォリオ構築モジュール
  - portfolio_builder.py: 候補選定 (select_candidates)、等金額/スコア重み (calc_equal_weights / calc_score_weights) を実装。スコア全てが 0 の場合のフォールバック警告を追加。
  - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジーム時のフォールバック動作を明記。
  - position_sizing.py: 株数算出ロジック (calc_position_sizes) を実装。risk_based / equal / score の配分方式、lot_size（単元株）丸め、単銘柄上限・アグリゲートキャップ、コストバッファを考慮したスケーリングロジックを実装。
  - portfolio パッケージのエクスポートを整備。
- 研究用（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルを前提とした SQL ベースの実装。
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）やランク変換・統計サマリー (rank, factor_summary) を実装。外部依存を抑えた純粋な Python 実装。
  - research パッケージのエクスポートを整備（zscore_normalize を data.stats から取り込むエイリアス含む）。
- ニュース NLP スコアリング（AI）モジュール
  - ai/news_nlp.py を実装（OpenAI API を利用して raw_news を集約・スコア化し ai_scores へ保存する処理を設計）。
  - タイムウィンドウ計算（calc_news_window）、API キー解決、バッチ処理・トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、レスポンス検証、スコアクリッピング（±1.0）、リトライ（指数バックオフ）など設計を反映。
  - JSON Mode を用いた厳密な JSON 出力期待や部分更新（DELETE → INSERT による置換）による部分失敗耐性の方針を明記。
- ツール: Paper Trading 検証レポート
  - tools/paper_verification_report.py を実装。paper_trading DB からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値に基づいた PASS/FAIL 判定を標準出力で出力する CLI ツールを実装。閾値はソース内定数で定義（稼働率 99% など）。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）を判別し、権限不足や未対応 OS では安定して警告を出してスキップする。
  - utils パッケージの基礎を追加。

Changed
- 環境値・挙動の明確化
  - モニタリングのポーリング間隔は MONITOR_POLL_INTERVAL 環境変数でオーバーライド可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出す。
  - .env ファイルのパーサは export 形式、クォート、エスケープ、インラインコメントの取り扱いに対応。既存 OS 環境変数は保護される（.env.local の強制上書きを防止）。
- DB 周りの扱い
  - 監視（monitoring）用テーブルの初期化処理（init_monitoring_db）を起動時に呼ぶことで、DB スキーマが存在しない場合でも冪等にテーブルを準備するように変更。
  - DuckDB と SQLite を併用する設計を明確化（分析用は DuckDB、監視/実行ログは SQLite）。

Fixed
- 不正な入力やデータ欠損時の堅牢性向上
  - factor / volatility / momentum 等の計算でデータ不足時に None を返す実装により、パイプライン全体での NULL 伝播やゼロ除算を回避。
  - position sizing / sector cap / price 取得失敗時のスキップ処理を追加（価格欠損時に不要な例外を発生させない）。
  - paper_verification_report の各クエリでテーブルが存在しない場合（OperationalError）にデフォルト値で処理を継続する保護を追加。

Security
- 環境変数取り扱いに関する注意
  - .env の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 側の環境変数は上書きされないよう保護される。

Known issues / Notes
- ai/news_nlp.py は堅牢な設計とリトライロジックを含むが、実行時のネットワーク/API レスポンスの取り扱い（レート制限や JSON 形式の厳密性）には運用上の注意が必要。
- position_sizing の price 欠損時の補完（前日終値や取得原価のフォールバック）は TODO コメントで示されている。将来的な拡張で精度向上が期待される。
- 一部モジュールは DuckDB / SQLite のスキーマ依存（prices_daily, raw_financials, raw_news 等）があるため、実運用前にスキーマ準備が必要。

References
- ソースコード参照: src/kabusys 以下の各モジュール（run_monitoring.py, run_execution.py, config.py, portfolio/*, research/*, ai/news_nlp.py, tools/*, utils/*）。

もし変更履歴の粒度（個別のコミット単位や日付付け）をより正確に再構成したい場合は、git のコミットログやリリースノート用の追加情報を提供してください。
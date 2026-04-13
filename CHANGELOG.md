CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
追加・改善
- 環境変数ローディングを強化
  - プロジェクトルートを .git / pyproject.toml から自動検出して .env / .env.local を読み込むように（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能）。
  - .env のパースを拡張：export 前置、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。既存の OS 環境変数を保護する protected オプションを採用。
- プロセス優先度・CPU Affinity のユーティリティを追加（utils.process_priority）
  - set_process_priority(level) により Windows / Linux / macOS を意識せず優先度設定を行えるように。
  - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（利用権限がない場合は警告でスキップ）。
  - 対応外 OS や権限不足時のフォールバック処理を追加。
- 実行コンポーネント改善
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じた DB 分離（paper_trading 用 DB を使用）や BrokerClientFactory の利用を組み込んだ起動処理を提供。
  - run_monitoring: SystemMonitor 用のポーリング起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視系は環境（開発/ペーパー）にかかわらず本番の sqlite_path を使用する挙動を明示。
  - 起動直後にプロセス優先度を "high" に設定する処理を共通化。
  - 監視ループでの例外を捕捉してログに残し、ループ継続するフェイルセーフを導入。KeyboardInterrupt を捕まえて正常終了するように。
- Paper Trading 周りの分離と支援ツール
  - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）、PAPER_FILL_MODE の設定（instant/partial/never/reject）を Settings でサポート。
  - tools/paper_verification_report を追加：Paper Trading DB から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計してレポート（PASS/FAIL）を表示。期間指定（--from / --to）・DB パス指定（--db）に対応。
  - レポートの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を定義し、自動判定を行う。
  - DB が存在しない場合のエラーメッセージを改善。
- DuckDB 統合
  - DuckDB 接続を各種解析・研究処理で受け取る設計に統一（research / ai / execution コンポーネントで利用）。
  - DuckDB を使った価格・財務データクエリを多用し、オンメモリ／ファイル DB 両方に対応。
- ポートフォリオ構築モジュールの追加・強化（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームは警告ログを出してフォールバック。
  - position_sizing: 各種配分方式（risk_based / equal / score）に基づく株数計算、単元株丸め、aggregate cap（利用可能現金に応じたスケールダウン）を実装。手数料・スリッページ考慮用の cost_buffer を追加。
- リサーチ（ファクター計算・特徴量探索）
  - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高指標）、バリュー（PER、ROE）を DuckDB から計算する関数を実装。データ不足時の None ハンドリングを明確化。
  - research.feature_exploration: 将来リターン（複数ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - 正確なランク計算（同順位は平均ランク）や計算不能ケース（サンプル数不足等）の扱いを定義。
- AI ニュース NLP モジュール（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約して、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に保存する処理を実装。
  - 扱いのポイント：記事数/文字数のトリム、バッチ（最大 20 銘柄）での API コール、429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の既存スコア保護（対象コードを限定して DELETE→INSERT）。
  - API キー未設定時は明示的エラーを返す仕様。
- 設定管理（kabusys.config）
  - Settings クラスで主要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、各 DB パス、監視閾値、PID/KILL ファイルパス、ログレベル等）を集中管理。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を追加して誤設定時に早期に失敗させる。
- 例外処理・堅牢性の改善
  - 各種クエリや集計で sqlite3.OperationalError をキャッチしてデフォルト値を返すなど、部分的なデータ欠損に対してフェイルセーフを導入。

変更・修正
- monitoring DB 初期化処理（init_monitoring_db）を起動時に必ず呼び出すようにして冪等性を保証。
- position_sizing のスケーリングロジックを改善し、残余キャッシュを用いた lot_size 単位での再配分アルゴリズムを採用。
- research / factor の SQL を最適化し、スキャン範囲にバッファ（日付バッファ）を導入して週末・祝日を吸収。
- tools.paper_verification_report の P95 算出や欠損データ処理を改善。

Fixed
- MONITOR_POLL_INTERVAL に 0 以下の値が設定された場合に発生しうる time.sleep の ValueError を回避するバリデーションを追加し、不正値時は警告を出してデフォルト値へフォールバック。
- .env の読み込みでファイルアクセス失敗時に警告を出すように変更（例外は上げず処理継続）。
- news_nlp: API の部分失敗で全体を壊さないように処理を分割してスコアの保全性を向上。

0.1.0 - 2026-04-13
------------------
初回公開リリース。以下を含む基盤的な実装を提供。

Added
- プロジェクト基本構成とバージョン情報（kabusys.__init__）。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプト（DB接続、Broker クライアント生成、ExecutionEngine 実行）。
  - run_monitoring.py: SystemMonitor 起動スクリプト（DB接続、ポーリングループ）。
- 設定管理モジュール（kabusys.config）
  - .env 自動ロード（.env / .env.local）、Settings クラスを追加。
- ユーティリティ
  - process_priority（優先度設定、CPU affinity）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder, position_sizing, risk_adjustment。
- リサーチ機能（kabusys.research）
  - factor_research（モメンタム、ボラティリティ、バリュー）。
  - feature_exploration（将来リターン、IC、統計サマリー）。
- AI ニューススコアリング（kabusys.ai.news_nlp） - プロトタイプ実装。
- 運用支援ツール
  - tools/paper_verification_report: Paper Trading 用検証レポート生成。

Changed
- 主要な I/O 操作での堅牢性を向上（DB初期化、存在チェック、例外処理の追加）。

Fixed
- - (初回リリースのため特記事項なし)

注記
- 本 CHANGELOG はコードベースから推測して作成した要約です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
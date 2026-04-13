CHANGELOG
=========

この CHANGELOG は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。
コードベースの内容から推測して変更点・導入機能を日本語でまとめています。

[Unreleased]
-------------

Added
- 全体
  - 新機能群を追加：ポートフォリオ構築、リスク調整、ポジションサイジング、ファクター計算、特徴量探索、ニュースNLP スコアリング、運用/監視起動スクリプトなど（各モジュール参照）。
- ai/news_nlp.py
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング機能を実装。
  - タイムウィンドウ（JST 基準 → UTC 変換）で対象記事を抽出し、銘柄ごとにテキストを集約してバッチ（最大20銘柄）で API 呼び出しを行う。
  - レスポンスのバリデーション、スコアの ±1.0 クリッピング、429/ネットワーク/5xx への指数バックオフリトライを実装。
  - ai_scores テーブルへの安全な置換（部分失敗時に既存スコアを保持できる設計）。
- research/
  - ファクター計算（calc_momentum、calc_volatility、calc_value）を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクターを算出。
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティを実装。
- portfolio/
  - 銘柄選定と重み計算（select_candidates、calc_equal_weights、calc_score_weights）を実装。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知セクターや未知レジームに対するフォールバックロジックあり。
  - ポジションサイズ計算（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）対応、lot_size 単位丸め、aggregate cap（利用可能現金にあわせたスケーリング）、cost_buffer による保守的見積り、端数処理ロジックを実装。
- tools/paper_verification_report.py
  - Paper Trading 用の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタリング、DB 存在チェックなどを実装。
- utils/process_priority.py
  - プロセス優先度・CPU affinity 設定ユーティリティを実装。Windows / POSIX (Linux, Darwin, FreeBSD) を透過的に扱う。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未サポート環境では警告を出して安全にスキップ。
- config.py
  - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み実装（環境変数で無効化可能）。
  - .env パーサーの強化（export プレフィックス、クォート、エスケープ、インラインコメント扱い、protected キー）。
  - Settings クラスを提供し、細かい設定（DB パス、paper_trading 用 DB、PID ファイル、監視閾値、PAPER_FILL_MODE の検証、KABUSYS_ENV の検証等）をプロパティで参照可能に。
- run_execution.py / run_monitoring.py
  - 起動スクリプトを実装。起動時にプロセス優先度を「high」に設定し、SQLite/DuckDB 接続を初期化。ExecutionEngine は paper_trading モード時に専用 DB を使用することで本番 DB と完全分離。
  - 監視ループは MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する仕様。

Changed
- logging
  - 起動スクリプトで logging.basicConfig(level=INFO) を設定し、起動時の環境ログを出力するように変更。
- DuckDB / SQLite の使用
  - 分析（research）およびニュース NLP は DuckDB 接続を受け取り SQL と Python を組み合わせて計算。Execution/Monitoring は DuckDB と SQLite を併用。

Fixed / Robustness improvements
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック（0 以下や非整数の入力時にデフォルトを使用して警告）。
- .env の読み込みでファイル読み込み失敗時に警告を出して継続するように変更（テストや CI で安全）。
- ニュース／ファクター計算系でデータ欠損時に None を返すことで集計やレポート生成での例外発生を回避（例: P95 計算空リスト、MA200 未満のデータなど）。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックして警告出力。
- calc_ic: 有効レコード数が 3 未満の場合は None を返す（計算不能の扱い）。

Removed / Deprecated
- なし（コードからは該当箇所なし）。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決し、未設定時は明示的にエラーを出して処理を中断。API キーのハードコードは行っていない点を明記。

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース（0.1.0）。以下の主要機能を含む大規模な機能セットを実装・公開。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine の起動、paper_trading モード分離、RiskManager/OrderManager/Reconciler の組み立て。
    - run_monitoring.py: SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL による調整。
  - 環境設定
    - config.py: .env 自動読み込み（プロジェクトルート検出）、Settings クラス、各種設定プロパティ（DB パス、PID/kill flag、しきい値、ログレベル等）。
  - ポートフォリオ構築
    - portfolio_builder.py: 候補選定・重み計算。
    - risk_adjustment.py: セクターキャップ、レジーム乗数。
    - position_sizing.py: 株数算出、aggregate cap、lot 単位丸め、risk_based 配分等。
  - 研究・分析
    - research.factor_research: momentum / volatility / value ファクターの計算（DuckDB ベース）。
    - research.feature_exploration: 将来リターン計算、IC、統計サマリー、ランク変換。
  - ニュース NLP
    - ai.news_nlp: raw_news を OpenAI でスコアリングし ai_scores に書き込む機能（バッチ処理、リトライ、レスポンス検証）。
  - ユーティリティ
    - utils.process_priority: プロセス優先度 / CPU affinity の設定ユーティリティ（クロスプラットフォーム対応）。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成ツール（CLI）。

Changed
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

Fixed
- 各モジュールでのデータ欠損ケース（NULL・空リスト）に対する安全なハンドリングを実装。

Notes / Known limitations
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_size サポートを検討）。
- apply_sector_cap は "unknown" セクターに対してはセクター上限を強制しない仕様（設計上の判断）。
- news_nlp は OpenAI API 呼び出しに依存するため、API キー・レート制限・ネットワーク状態に注意が必要。
- DuckDB の executemany 等の実装依存事項に対して注意書き（コード内コメントあり）。

脚注
- この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。正確な履歴は Git のコミットログをご参照ください。
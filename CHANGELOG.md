CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（ありません）

0.1.0 - 2026-04-17
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージ説明を src/kabusys/__init__.py に定義。

- 実行・監視用エントリポイントを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV が paper_trading のときは paper_trading 専用 SQLite（data/paper_trading.db）を使い、本番 DB と分離する挙動を実装。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）検知による安全停止処理、実行用 PID ファイル管理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用することを明確化。
    - 停止フラグ検知、例外キャッチとログ出力、接続クローズ処理を実装。

- 設定・環境読み込みユーティリティを追加。
  - src/kabusys/config.py
    - .env/.env.local の自動ロード（OS 環境変数を保護して上書き制御）。
    - .git / pyproject.toml を基準にプロジェクトルート探索（配布後も動作）。
    - export KEY=...、クォート文字列、エスケープ、行末コメント解析等を考慮した .env パーサを実装。
    - 環境変数必須チェック（_require）と Settings クラス（各種設定プロパティ）を実装。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーションとデフォルト値を提供。

- Execution 系コンポーネント（参照実装／接続点）。
  - src/kabusys/execution/* 関連コンポーネント（ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory 等）を統合して起動できる流れを用意（スクリプトからの組立てを確認）。

- 監視 DB 初期化の統合。
  - run_* スクリプトで init_monitoring_db を呼び、監視テーブルの存在を保証。

- プロセス優先度・CPU 固定ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) により Windows / POSIX 両対応で優先度設定（High/Normal/Low）を試行。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピン止め可能。
    - psutil の権限不足や未対応環境を考慮したフォールバック動作（警告ログ）を実装。

- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群を追加。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、同点時の tie-break）、等金額配分、スコア正規化配分（スコア全て 0 の場合は等金額にフォールバック）を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知セクター扱い、価格欠損時の注意点をドキュメント化。
  - src/kabusys/portfolio/position_sizing.py
    - risk_based / equal / score の配分方式に対応した株数計算を実装。
    - lot_size（単元）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮したアルゴリズムを実装。
  - src/kabusys/portfolio/__init__.py で上記 API を公開。

- リサーチ・特徴量計算モジュールを追加（DuckDB を前提）。
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対 ATR、出来高指標）、Value（PER, ROE）ファクター計算を実装。
    - DuckDB SQL を用いた window 関数ベースの実装でデータ不足時の None ハンドリングを行う。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意 horizon）、Spearman ランク相関 (IC) 計算、ファクター統計サマリ（count/mean/std/min/max/median）を純粋関数で実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize は kabusys.data.stats からインポート）。

- ニュース NLP スコアリング機能を追加（OpenAI 統合）。
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込むワークフローを実装。
    - バッチサイズ、文字数/記事数の上限、ターゲット時間窓（JST→UTC 変換）や厳密な JSON 出力要請を仕様化。
    - 429 / ネットワーク / 5xx などに対する指数バックオフとリトライロジック、レスポンス検証、スコアのクリップ処理、部分書き換え（該当コードのみ DELETE→INSERT）などを備える（API キー指定必須）。
    - calc_news_window() 等のユーティリティを実装。
    - API キー未設定時の ValueError を明示。

- 検証ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading DB（デフォルト data/paper_trading.db）から期間指定でレポートを生成する CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標取得 SQL と閾値判定（PASS/FAIL）を提供。
    - コマンドライン引数 --from/--to/--db に対応。

Changed
- 環境変数の取り扱いを厳密化。
  - Settings による env/log level/bool/数値パラメータのバリデーションを追加。
  - PAPER_FILL_MODE の有効値チェックを追加し、不正値は ValueError を投げる。

- 実行時の堅牢性改善。
  - run_monitoring/run_execution においてプロセス優先度を起動直後に設定。
  - ポーリングループやエンジン実行スレッドで例外を広くキャッチし、ログに残して継続するように変更。
  - DB 接続後の finally での確実なクローズ処理を実装。

Fixed
- .env パーサの挙動改善。
  - export プレフィックス、クォートされた値内のバックスラッシュエスケープ、行末のインラインコメント判定を正しく処理するよう修正。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを導入。

- データ不足状況での None ハンドリングを明示。
  - ファクター計算やレイテンシ集計、orders/risk クエリ等で該当ケース時に None を返し上位で適切に扱えるようにした。

Security
- OpenAI API キーの取り扱いについて未設定時に明示的なエラーを出すことで、誤った無効 API 呼び出しを回避。

Notes
- DuckDB / SQLite / psutil / openai など外部依存があるため、本リリースの動作には環境整備が必要です。
- 一部のモジュール（例: execution 内の具体的な実装、monitoring_db の詳細、kabusys.data.stats 等）は本 changelog の作成時点で参照実装を前提としています。

Breaking Changes
- なし（初期リリース）

--- 

今後のリリースでは以下を想定しています（例）:
- 単元分割（銘柄別 lot_size）対応、手数料・スリッページの詳細モデル化
- News NLP の並列化・レート制御強化、失敗時のリトライ耐性向上
- テストカバレッジの拡充と CI 用の環境セットアップドキュメント追加
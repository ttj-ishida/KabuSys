CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-17
-----------------

Added
- 初回リリースとして主要機能を追加しました（パッケージバージョン: 0.1.0）。
  - コア設定と環境変数読み込み（src/kabusys/config.py）
    - プロジェクトルート探索により .env / .env.local を自動読み込み（OS 環境変数保護あり）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env のパース拡張:
      - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いに対応。
    - Settings クラスで各種設定値を提供（DB パス、PID/フラグパス、監視閾値、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証等）。
  - 起動スクリプト
    - 監視ループ起動: src/kabusys/run_monitoring.py
      - プロセス優先度を起動時に "high" に設定。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する（意図的な設計）。
      - 停止フラグファイル data/stop_requested.flag を検出してループを終了。
    - 実行エンジン起動: src/kabusys/run_execution.py
      - プロセス優先度を起動時に "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine をスレッドで実行。
      - 停止フラグ検知時にエンジンを停止。
  - 監視 DB 初期化ユーティリティの利用（init_monitoring_db を実行して監視テーブルの存在を保証）。
  - ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
    - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
      - スコア降順＋signal_rank でタイブレーク。
      - 全スコアが 0 の場合は等重配分へフォールバック（警告出力）。
    - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
      - 既存保有のセクター比率が閾値以上なら、そのセクターの新規候補を除外。
      - レジーム毎の資金乗数: bull=1.0, neutral=0.7, bear=0.3（未知レジームは 1.0 にフォールバック）。
    - 銘柄ごとの発注株数決定（calc_position_sizes）
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）で丸め、単銘柄上限・総投下上限（aggregate cap）を考慮。
      - cost_buffer による保守的コスト見積り、総コスト超過時のスケーリングと残差に基づく再配分ロジック実装。
      - 価格欠損時のスキップやログ出力を考慮。
  - 研究（リサーチ）モジュール（src/kabusys/research/*）
    - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け prices_daily / raw_financials を参照）。
      - Momentum（1m/3m/6m）、MA200乖離、ATR20、20日平均売買代金等を計算。
      - データ不足時には None を返す設計。
    - 特徴量探索: calc_forward_returns（任意ホライズン）、calc_ic（スピアマンランク IC）、factor_summary（基本統計）、rank（同順位は平均ランク）。
      - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news から銘柄別に記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を計算し ai_scores テーブルへ書き込み。
    - バッチサイズ、トークン肥大対策（記事数・文字数上限）、最大リトライ、指数バックオフ、レスポンスの JSON 検証、スコアのクリップ等を実装。
    - ニュース収集ウィンドウ（JST基準→UTC変換）を calc_news_window で提供し、ルックアヘッドバイアスを防止。
    - API キー未設定時は明示的なエラーを発生させる。
  - ツール（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と基準値による PASS/FAIL 判定を出力。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
  - ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority(level) により Windows / POSIX を吸収した優先度設定を提供。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を固定するヘルパを提供。
    - 権限不足や未サポート環境では警告を出し処理をスキップするフォールトトレラントな実装。
  - パッケージ情報（src/kabusys/__init__.py）
    - __version__ = "0.1.0" を設定。

Changed
- 初回リリースのため履歴は追加のみ。

Fixed / Improved
- .env パーサの堅牢化（クォート・エスケープ・コメント処理の改善）。
- DuckDB を分析用途（research / ai）で明示的に使用する設計とし、SQL 内でのウィンドウ関数や ROWS 範囲を活用して効率的に計算するよう改善。
- position_sizing の aggregate cap 処理で残差を考慮した再配分ロジックを追加（再現性確保のため安定ソートを採用）。

Notes / Known limitations
- run_monitoring は「監視は環境に関わらず本番 sqlite_path を使用する」仕様です。paper_trading 環境での監視分離が必要な場合は運用設計に注意してください。
- position_sizing 内で価格が欠損（0.0）の場合、現在はスキップしているのみで、将来的に前日終値や取得原価などによるフォールバックを検討中（コード内に TODO コメントあり）。
- ai.news_nlp は OpenAI API に依存します。API の利用制限・レート制限・課金などは運用者が管理してください。レスポンスバリデーションを行いますが、外部サービスの大幅な仕様変更があった場合は影響を受けます。
- tools/paper_verification_report は対象 DB に期待されるテーブル（system_status, trade_logs, risk_logs 等）が存在しない場合に OperationalError をキャッチして N/A 表示する設計です（堅牢性優先）。
- DuckDB の executemany やバージョン固有の挙動に依存する箇所があるため、DuckDB バージョン差異には注意してください（コード中に扱いをコメント）。

Security
- 本リリースでは特にセキュリティ修正は含まれていません。環境変数や API キーの取り扱いは運用上の注意が必要です（OPENAI_API_KEY 等）。

Acknowledgments / Credits
- 初版の実装・設計方針はソースコード内のドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいています。

---
注: 上記はソースコードの実装内容および内包コメントから推測して構成したリリースノートです。実際のリリース時にはビルド・配布方法や追加の変更点に応じて更新してください。
CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠します。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------
（なし）

v0.1.0 - 2026-04-17
-------------------

Added
- 基本バージョンを追加（__version__ = 0.1.0）。
- 実行 & 監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 環境（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、paper_trading 専用 DB（data/paper_trading.db または環境変数で指定）に完全分離して記録する。実行中の停止フラグ・PID 管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する設計。
- 設定管理モジュールを追加
  - kabusys.config.Settings クラスを導入。.env 自動読み込み（.env → .env.local、OS 環境変数の保護）・エクスポート形式や引用符・コメントの堅牢なパース・必須キー取得ヘルパーを実装。
  - 各種環境変数に対するバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）とデフォルト値を提供。
- Paper Trading 検証ツールを追加
  - kabusys.tools.paper_verification_report: Paper Trading DB から期間指定で検証レポートを生成する CLI ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値に基づく PASS/FAIL 判定を行う。
- ポートフォリオ構築ライブラリを追加
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を計算（スコア全体が 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（max_sector_pct）に基づく候補の除外処理を実装。売却予定銘柄の除外・unknown セクターの扱いなどを考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（既定値: bull=1.0, neutral=0.7, bear=0.3）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: 重み・候補・利用可能現金等に基づき実際の発注株数を計算。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、ポジション上限・aggregate cap（利用可能現金に合わせてスケールダウン）、手数料/スリッページ考慮（cost_buffer）、端数分配ロジックを実装。
- 研究 / ファクター計算ライブラリを追加
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials テーブルを利用してモメンタム/ボラティリティ/バリュー系ファクターを計算。
    - ファクター計算はウィンドウサイズやデータ不足時の None ハンドリングなどを考慮。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得。
    - calc_ic: ファクターと将来リターンのスピアマン IC を計算（ランク処理を含む）。有効レコードが 3 未満の場合は None を返す。
    - factor_summary / rank: 基本統計量やランク付けユーティリティを提供。外部ライブラリに依存せず標準ライブラリのみで実装。
- ニュース NLP スコアリングモジュールを追加（AI 統合）
  - kabusys.ai.news_nlp:
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を計算。
    - score_news の骨格を実装（OpenAI API を使用）。機能設計としては記事集約・銘柄ごとのトリミング、最大 20 銘柄バッチ、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）、部分失敗時の DB 保護（対象コードのみの置換）などを想定。
    - 使用モデルは gpt-4o-mini、厳密な JSON 出力を要求するシステムプロンプトを用意。
- ユーティリティを追加
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows/Linux/Mac 等の差異を吸収してプロセス優先度を設定。アクセス権限や未対応 OS に対して安全にフォールバック。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を設定するユーティリティ（利用不可時は警告とスキップ）。
- DB 初期化ユーティリティ利用
  - run_* スクリプトは監視用テーブルが存在しない場合に備えて init_monitoring_db を呼び出す（冪等）。

Changed
- .env の自動読み込み仕様を導入・明確化
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export KEY=val 形式・クォート内のエスケープ・インラインコメント扱い等に対応。
  - OS 環境変数は protected として上書きされない（.env.local の override は可能だが protected は保護）。
- 設定周りのデフォルトパスを明示（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
- 実行/監視スクリプトの起動時にプロセス優先度を最初に設定するよう変更（set_process_priority("high")）。

Fixed
- なし（初回リリース相当の追加が中心）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーが未設定の場合に score_news が ValueError を投げて明示的に失敗するようにし、キー漏洩のリスクを低減（環境変数の読み取りに依存）。

Notes / 補足
- research / ai / portfolio モジュールは DuckDB/SQLite のローカルデータを前提としており、本番ブローカー API と発注処理は ExecutionEngine 側で分離されています（paper_trading モードは DB とブローカーの完全分離を想定）。
- news_nlp モジュールはファイル末尾で途中まで実装されているため、実運用前に完全な記事集約・API 呼び出し・DB 書き込み部分の実装とテストが必要です。
- 各種閾値（paper_verification_report の閾値、RiskManager のデフォルト設定等）はコード中に定数として置かれており、将来は設定化することを想定。

今後の予定（例）
- news_nlp の API 呼び出し・DB 書き込み処理の完成とリトライロジックの検証。
- 単元株情報の銘柄別取り扱い（lot_size を銘柄別にする設計への拡張）。
- テストカバレッジ強化（特に position_sizing のスケールダウン / 端数配分ロジック、.env パーサーのエッジケース）。
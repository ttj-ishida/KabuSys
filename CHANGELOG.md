CHANGELOG
=========

すべてのリリースは Keep a Changelog のフォーマットに準拠して記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本アプリケーション初回公開
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 実行系 / 監視の起動スクリプト
  - run_execution.py: ExecutionEngine の起動エントリポイントを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、engine.run_session() の実行を行う。
    - paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離する挙動を実装。
    - RiskManager のデフォルト設定（最大ポジション比率、利用率、レートリミット、サーキットブレーカーなど）を構成。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に production 相当の sqlite_path を使用する旨を明記。

- 環境設定 / ロード機構
  - config.py:
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み実装（.env → .env.local、OS 環境変数を保護）。
    - .env パースの堅牢化（export 形式、クォート／エスケープ、行末コメント取り扱いなど）。
    - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 関連、監視閾値、PID/KILL ファイルパス、環境判定ユーティリティ等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - 各種設定値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py:
    - シグナルの候補選定（スコア降順・タイブレークロジック）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）：既存保有のセクターエクスポージャーを計算し、超過セクターの新規候補を除外。
    - レジームに応じた乗数計算（calc_regime_multiplier）：bull/neutral/bear をマップし未知レジームはフォールバック。
  - portfolio/position_sizing.py:
    - allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、ポジション上限・aggregate cap のスケールダウンロジック、cost_buffer を考慮した保守的見積もりと再配分ロジックを実装。
    - 将来的な拡張（銘柄別 lot_size のサポート）についてコメントあり。

- 研究・ファクター計算
  - research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー系ファクター計算を DuckDB（prices_daily / raw_financials テーブル）上で実装。200日移動平均、ATR、出来高指標、EPS/ROE 組合せ等を算出。
    - データ不足時は None を返す設計（堅牢性確保）。
  - research/feature_exploration.py:
    - 将来リターン計算（複数ホライズンをまとめて1クエリで取得）、Spearman（ランク）を用いた IC（Information Coefficient）計算、rank / factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を用いず標準ライブラリのみで実装。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）を用い銘柄ごとのセンチメント（-1.0〜1.0）を計算し ai_scores テーブルへ書き込む処理を実装。
    - バッチ（最大 20 銘柄/回）、記事文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアのクリップ、部分失敗時の既存スコア保護（対象コードのみ DELETE→INSERT）などを備える。
    - API キーが未設定の場合はエラーとする（明示的に api_key 引数または OPENAI_API_KEY が必要）。

- ユーティリティ
  - utils/process_priority.py:
    - cross-platform のプロセス優先度設定（Windows / POSIX 対応）、CPU affinity 設定機能を提供。権限不足や未対応 OS の場合は警告を出してスキップするよう堅牢化。
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し PASS/FAIL を判定する。
    - 検証閾値はソースに定義（稼働率 >= 99%、成立率 >= 90% 等）。DB パスは引数/環境変数で指定可能。

- DB / ストレージ関連
  - DuckDB と SQLite を組み合わせた設計を採用（分析と運用の責務分離）。
  - monitoring_db の初期化呼び出しを起動スクリプトで実行してテーブルの存在を担保（冪等）。

Changed
- なし（初回公開）

Fixed
- 実運用を想定した堅牢性改善（初版実装時点での注意点としてソース内にエラーハンドリングやフォールバック挙動を多数明示）
  - MONITOR_POLL_INTERVAL の不正値時にデフォルトへフォールバックするログを追加（run_monitoring.py）。
  - .env 読み込み時のファイル読み込み失敗で警告を出すことで静かに失敗するケースを把握可能に（config.py）。
  - process_priority / cpu_affinity で権限不足や未実装 API に対し警告を出してスキップ（utils/process_priority.py）。
  - DuckDB の executemany に関する注意（ai.news_nlp.py 内コメント）など運用上の落とし穴を注記。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される点を TODO コメントで指摘（前日終値や取得原価でのフォールバックを検討）。
- position_sizing:
  - 将来的に銘柄別 lot_size を導入する旨の TODO コメントあり。
- ai/news_nlp:
  - 大量記事やレスポンス不整合に対する運用上の監視やリトライ波及範囲の調整が必要（初期実装では堅牢化済みだが運用観察が必要）。
- テストカバレッジ:
  - 外部 API や DB に依存する部分が多く、ユニット / 統合テストを用いた運用検証を推奨。

作者注
- 本 CHANGELOG はソースコード内のコメント・実装から推測して作成した初回の変更履歴です。実際のリリースノート作成時は挙動確認・追加のドキュメント（例: PortfolioConstruction.md, StrategyModel.md）があればそれらを参照して追記してください。
CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
慣例に従い、セマンティックバージョニングを想定しています。

Unreleased
----------
（現時点のリポジトリスナップショットを反映した想定変更点 — 次回リリース候補）
- 追加
  - ニュースNLP (kabusys.ai.news_nlp)
    - OpenAI（gpt-4o-mini）を用いたニュース記事のセンチメントスコアリング機能を追加。
    - 記事集約・バッチ送信（最大20銘柄/チャンク）、スコアの ±1.0 クリッピング、取得結果の部分置換（DELETE + INSERT）による堅牢な書き込みフローを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ方式のリトライを実装。
    - タイムウィンドウ計算（JST基準）や記事数・文字数上限（トークン肥大化対策）を実装。
  - リサーチ機能 (kabusys.research)
    - factor_research: Momentum / Volatility / Value といった定量ファクター計算を DuckDB 経由で追加。
    - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（スピアマン準拠）計算、ファクター統計サマリー、ランク付けユーティリティを追加。
    - DuckDB を利用した設計で外部APIに依存しない純粋計算モジュールとして実装。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder: シグナル選定と等分配・スコア加重配分アルゴリズムを追加。
    - position_sizing: risk_based / equal / score の各割付方式、単元株丸め、aggregate cap スケーリング（cost_buffer を考慮）を実装。
    - risk_adjustment: セクター上限適用ロジックと市場レジームに応じた投下資金乗数（bull/neutral/bear）を追加。
  - 実行系 / 監視
    - run_execution: ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用し、本番DBと分離。
    - run_monitoring: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 両スクリプトとも起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
  - 設定管理 (kabusys.config)
    - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を探索）。.env / .env.local の読み込み優先度を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを追加。
    - .env パーサは export 付き行、引用符付き値（エスケープ対応）、行末コメントの扱いをサポート。
    - Settings クラスで多数の設定プロパティを提供（DB パス、paper_trading 用パス、PID/KILL フラグ、閾値、env/log_level の検証など）。
  - ユーティリティ (kabusys.utils.process_priority)
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足等の例外は警告してスキップする安全設計。
  - ツール
    - paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。稼働率 / 注文成功率 / 送信率 / レイテンシ(P95) 等を算出し PASS/FAIL を判定する。
  - パッケージメタ
    - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

- 変更（設計上の注意点）
  - DuckDB を調査・研究系や AI モジュールの主要ストレージ連携に採用。prices_daily / raw_financials / raw_news 等を SQL で集計する設計に統一。
  - paper_trading モード時の DB 分離強化（paper_sqlite_path を利用）により、本番データへの影響を最小化。
  - .env 読み込み時に OS 環境変数を保護（protected set）し、.env.local は上書き可能だが OS 環境は上書きしない運用に設計。

- 既知の制約・改善予定
  - position_sizing の price 欠損時の扱い（price=0 の場合にエクスポージャーが過少見積もられる）について注釈と将来的なフォールバック実装（前日終値等）を記載。
  - AI スコアの書き込みは部分置換を行うが、チャンク全体が失敗した場合の補償処理は限定的（ログとスキップ） — 運用上の再実行が必要。

v0.1.0 - 2026-04-12
-------------------
- 初回リリース（ベースライン実装）
  - 追加
    - コア機能: 設定管理（kabusys.config）、環境自動読み込み、Settings オブジェクト。
    - 実行/監視: run_execution.py, run_monitoring.py を追加。起動時のプロセス優先度設定と DB 初期化（init_monitoring_db）を実装。
    - 実行エンジン周辺: BrokerClientFactory, ExecutionEngine 起動フロー、OrderRepository / OrderManager / Reconciler / RiskManager の組立てとデフォルト設定（RiskConfig 等）。
    - 監視DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）。
    - ポートフォリオ構築: 銘柄選定、重み計算、単元丸め・スケーリングを含む position sizing ロジック。
    - リサーチ: ファクター計算（モメンタム・ボラティリティ・バリュー）と解析ユーティリティ（IC、統計サマリ等）。
    - AI ニューススコアリング（OpenAI 連携の初期実装）、スコアの整形と DuckDB への書込方針。
    - ユーティリティ関数: process_priority（優先度・affinity 管理）。
    - ツール: paper_verification_report CLI。
  - 変更
    - パッケージ構成を整理し、kabusys パッケージ下に execution / monitoring / portfolio / research / ai / utils / tools を配置。
  - ドキュメント
    - 各モジュールに docstring と設計方針を追加（PortfolioConstruction.md / StrategyModel.md 等を参照する旨を記載）。
  - 注意点（breaking）
    - Settings の一部プロパティは厳密チェックを行う（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。無効値や未設定の必須環境変数は ValueError を送出するため、既存環境の見直しが必要。
    - news_nlp.score_news は OpenAI API キーの存在を必須化（未設定時は ValueError）。運用環境では OPENAI_API_KEY を設定する必要あり。

過去のリリース履歴
-----------------
（初回リリースのため省略）

注記
----
- 本 CHANGELOG は提示されたコードベースからの推測に基づき作成しています。実際のコミット履歴や Issue トラッカーの記録がある場合はそちらを優先してください。
- セキュリティ関係の修正や重要な互換性破壊（breaking changes）はリリースノートで明確に告知することを推奨します。
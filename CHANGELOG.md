CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付はリポジトリ内の現状コードから推測した「初回リリース日」を設定しています。

Unreleased
----------

- 開発中の小変更やドキュメント修正をここに記載します。

0.1.0 - 2026-04-13
------------------

初回公開リリース。以下の主要機能・設計方針を実装しました。

Added
- 基本パッケージ
  - kabusys パッケージを追加。バージョン __version__ = "0.1.0" を設定。
  - パッケージ公開用の __all__ に主要サブパッケージを追加（data, strategy, execution, monitoring）。

- 設定と環境読み込み (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 環境変数のパース機能を実装（クォート／エスケープ／コメント処理に対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、各種設定値（DBパス、APIキー、監視閾値、環境種別など）をプロパティで提供。
  - 環境変数の検証・デフォルト処理（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。構成要素（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定する機能を呼び出す。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視側（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計。

- プロセスユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）で優先度を抽象化して設定可能に。
  - set_cpu_affinity(cpu_count) を追加し、プロセスの CPU affinity を最初の N コアに固定する機能を提供（未指定時は全コア）。
  - 権限不足や未サポート環境での安全にフォールバックする挙動を実装（例: AccessDenied を警告ログでスキップ）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選別 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合のフォールバック挙動を含む。
  - risk_adjustment: apply_sector_cap（セクター集中の除外ロジック）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。unknown セクターの扱い・ログ出力を含む。
  - position_sizing: calc_position_sizes を実装。risk_based / equal / score の割当方式をサポートし、lot 単位丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り、残差処理による切り上げ分配等を実装。

- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB を用い prices_daily / raw_financials を参照。
  - feature_exploration: 将来リターン算出（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、rank、統計サマリー（factor_summary）を実装。外部ライブラリ非依存の純粋実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI (gpt-4o-mini) でセンチメントスコア化し ai_scores テーブルへ書き込む処理を実装（score_news）。
  - バッチ処理（最大 20 銘柄/リクエスト）、記事・文字数のトリム（1銘柄あたり最大記事数／文字数制限）を実装。
  - リトライ（429/ネットワーク/5xx）に対する指数バックオフと上限、レスポンスの厳格なバリデーション、スコアの ±1.0 クリップを実装。
  - API キーの解決（引数または環境変数 OPENAI_API_KEY）と未設定時の明確なエラーを実装。
  - スコア書き込みは部分失敗時の安全性を考慮（更新対象コードを削ってから挿入）。

- ツール（kabusys.tools）
  - paper_verification_report.py を追加。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を集計し CLI で検証レポートを出力。
    - 指標：稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など。
    - 日付フィルタ（--from/--to）、--db オプションを提供。ファイル存在チェックと DuckDB 等に依存しない sqlite3 ベース実装。
    - Pass/Fail 基準と判定ロジックを実装（閾値を定数で定義）。

- DB 初期化 / 互換性
  - run_* スクリプトで monitoring テーブルの存在を保証する init_monitoring_db 呼び出しを追加（冪等処理）。
  - DuckDB と sqlite3 の両方を利用する設計を採用（研究・分析は DuckDB、軽量履歴は SQLite）。

Changed
- 設計方針の明示
  - ほとんどの研究・ポートフォリオ関数は DB を直接変更せず「純粋関数（メモリ内計算）」として設計。これによりテスト可能性・再現性を向上。

- 環境変数の扱い
  - .env.local は .env より優先して上書き（protected による OS 環境変数保護あり）。
  - Settings の各プロパティで入力値検証を強化（有効値チェック・例外メッセージ整備）。

Fixed
- 安全性とフェイルセーフ
  - process_priority / cpu_affinity 周りで権限がない場合に例外で停止しないように修正（警告ログでスキップ）。
  - OpenAI 呼び出しにおける API 失敗時の挙動をフェイルセーフ化（個別チャンク失敗時も他チャンクを継続）。

Notes / Implementation details
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid
- paper_trading 環境は本番データと完全分離する設計（専用 SQLite を使用）。
- NEWS ウィンドウや各種ウィンドウ定義は JST/UTC 変換を明示的に行い、ルックアヘッドバイアスを避ける実装方針。
- DuckDB クエリは大規模データを想定したウィンドウ関数／集計を活用しており、データ不足時は None を返すなど頑健性を担保。

Security
- API キー・機密情報は Settings 経由で環境変数として扱う設計。自動 .env 読み込みでは既存 OS 環境変数を上書きしない保護を実装。

今後の予定（例）
- BrokerClient の詳細なコネクション管理やリトライ・レート制御の強化
- 銘柄別 lot_size のマスタ管理対応
- research モジュールのパフォーマンス最適化（DuckDB クエリチューニング）
- ai.news_nlp の部分失敗時のロールバック/トランザクション改善

変更点や不足事項で補足が必要でしたら、実装箇所（ファイル/関数名）を指定していただければ、さらに詳細な changelog エントリを生成します。
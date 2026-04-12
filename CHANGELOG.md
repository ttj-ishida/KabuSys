CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

テンプレート・日時
-----------------
- 日付: 2026-04-12（コードベースのスナップショットから推測して作成）

Unreleased
----------
- 開発中の変更・今後の改善点はここに記載します。

[0.1.0] - 2026-04-12
-------------------

Added
- 初期リリースを公開。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用。起動時にプロセス優先度を "high" に設定し、DB (SQLite / DuckDB) に接続してセッションを開始する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理:
  - config.py: .env/.env.local の自動読み込み機能を実装（プロジェクトルートの .git または pyproject.toml を探索して判定）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。堅牢な .env パーサを実装し、クォート・エスケープ・コメント処理を考慮。OS 環境変数を保護する protected 機構を導入。
  - Settings クラス: 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 等）。環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: BUY シグナル候補選別（スコア降順、signal_rank によるタイブレーク）、等金額配分・スコア加重配分を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。risk_based / equal / score 各方法の実装、lot_size 単位で丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）対応。
  - portfolio/__init__.py: 主要関数をエクスポート。
- 研究（Research）機能:
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB SQL 経由で実装（prices_daily / raw_financials を参照）。MA200 や ATR 等を考慮した実装。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、安定なランク化ユーティリティを実装。外部ライブラリに依存しない純粋 Python 実装。
  - research/__init__.py: 主要関数をエクスポート（zscore_normalize を data.stats から取り込み）。
- AI / ニュース NLP:
  - ai/news_nlp.py: raw_news から記事を集約して OpenAI (gpt-4o-mini) を用いてセンチメントを算出し、ai_scores テーブルへ書き込むワークフローを実装。記事トリミング（1銘柄当たり記事数・文字数制限）、バッチ分割（最大 20 銘柄/コール）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）、部分更新（対象コードに限定した DELETE → INSERT）などの堅牢性設計を導入。ルックアヘッドバイアス回避のため datetime.today() を参照しない設計。
- ユーティリティ:
  - utils/process_priority.py: Windows と POSIX を吸収するプロセス優先度設定ユーティリティを導入。set_process_priority(level) で high/normal/low をサポート。set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加（利用できない場合は警告してスキップ）。
- 監視・検証ツール:
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの冪等的初期化をサポート（run_execution/run_monitoring から呼び出し）。
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し、PASS/FAIL 判定を行う。日付フィルタ/DB パス指定をサポート。P95 の計算や欠損データハンドリングを実装。

Changed
- DB 分離:
  - 実行エンジン実行時に paper_trading 環境では専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用するよう設計。本番データと紙トレードデータを完全分離。
- デフォルト設定とログ:
  - 複数のパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など）に対してデフォルトパスを定義し、Settings を通じて一元管理する設計に統一。
- 環境変数パース:
  - .env のパースロジックを強化（export プレフィックス、引用符・エスケープ、インラインコメントの扱いなど）。

Fixed
- 環境変数の安全性/堅牢性:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対してデフォルト値へフォールバックし、警告ログを出すように修正（run_monitoring.py）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの許容値検証を Settings 内で行い、不正な値は例外で明確に知らせるようにした。
- リソースクリーンアップ:
  - run_execution/run_monitoring で finally ブロックにより SQLite/DuckDB 接続を確実にクローズするように改善。

Security
- シークレット取り扱い:
  - Settings._require による必須環境変数の明示的検出。OpenAI API キー等が未設定の場合は明確なエラーを出す（ai/news_nlp.py）。
- ルックアヘッドバイアス対策:
  - ニュース NLP 処理で datetime.today() を使用せず、target_date ベースのウィンドウで処理する設計により、評価時のルックアヘッドを防止。

Notes / Implementation details
- DuckDB を分析処理（prices_daily, raw_financials, ai_scores 等）に利用。SQL ウィンドウ関数を活用して高速に集計・ウインドウ集計を行う設計。
- position_sizing の aggregate cap スケーリングは小数スケール → lot_size 単位で再割当てするアルゴリズムを実装。端数再配分は残差の大きい順に lot_size 単位で配分。
- apply_sector_cap は "unknown" セクター（未登録銘柄）に対してセクター上限を適用しない設計。
- ai/news_nlp は OpenAI の JSON Mode を前提とした厳密な JSON 出力の検証を行い、部分失敗時にも他銘柄スコアを保護するために対象コードで限定的な置換を行う。

今後の課題（参考）
- 単元株情報や銘柄別 lot_size を外部マスタから取り込む拡張（position_sizing の TODO）。
- run_monitoring のプロセス監視におけるより詳細なアラート・通知機能（LINE 連携など）。
- ai/news_nlp のエラーハンドリング・再試行ポリシーのさらに細かい調整（バックオフ・並列化）。
- DuckDB のスキーマ/テーブル定義やマイグレーション管理の明文化。

その他
- パッケージバージョンは __version__ = "0.1.0" を初期設定。

---
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や意図とは異なる可能性があります。必要であれば各変更点をコミット単位で分解してより詳細な履歴を作成できます。）
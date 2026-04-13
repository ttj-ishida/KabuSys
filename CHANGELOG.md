KEEP A CHANGELOG
=================

このプロジェクトは「Keep a Changelog」規約に従って変更履歴を管理します。
セマンティック バージョニングを採用しています（https://semver.org/）。

Unreleased
----------
（現在の作業ブランチ用 — 次回リリースで移動）

0.1.0 - 2026-04-13
-----------------
Added
- 基本リリース: KabuSys 初期機能群を追加。
- 実行エントリ:
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。BrokerClientFactory を利用したブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine.run_session() を呼び出す処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。起動時にプロセス優先度を "high" に設定し、SQLite/DuckDB 接続の初期化と安全なクローズを行う。
- 設定管理:
  - config.py: .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。.env と .env.local の読み込み順を実装し、OS 環境変数を保護する仕組みを導入。行パーサは export プレフィックス、引用符付き・エスケープ、インラインコメント等に対応。各種設定プロパティ（パス、しきい値、環境判定、paper_fill_mode の検証など）を提供。
- 監視・ユーティリティ:
  - monitoring_db 初期化呼び出しをエントリポイントに追加（冪等な初期化保証）。
  - utils/process_priority.py: プラットフォーム抽象化されたプロセス優先度設定を追加（Windows と POSIX の差を吸収）。CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供。権限不足等の例外は警告でスキップするフェイルセーフを実装。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークの signal_rank）と等金額/スコア加重重み計算を実装。スコア全体が 0 の場合は等金額配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（売却予定銘柄除外、"unknown" セクターは制限除外）、市場レジームに応じた乗数 calc_regime_multiplier を実装（'bull'/'neutral'/'bear' をサポート、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。単元（lot_size）丸め、銘柄ごとの上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer を用いた保守的コスト見積り、残差処理による追加配分を実装。
- 研究（Research）:
  - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム: 1M/3M/6M、MA200乖離; ボラティリティ: ATR20、平均売買代金、volume ratio; バリュー: PER/ROE）を実装。prices_daily / raw_financials テーブルのみ参照する仕様。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、Spearman ランク相関による IC 計算（rank, calc_ic）、ファクター統計サマリを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニュース NLP:
  - ai/news_nlp.py: raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄別センチメント (±1.0) を ai_scores テーブルへ書込むロジックを実装。記事/文字数トリム、バッチサイズ、リトライ（429/ネットワーク/5xx 用の指数バックオフ）、応答 JSON の検証、部分書き換え（該当コードのみ DELETE→INSERT）により部分失敗耐性を確保。ニュースウィンドウ（JST）計算ユーティリティも提供。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。期間指定オプション（--from / --to）および DB パス指定（--db）に対応。システム安定性（稼働率）、注文成功率/送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL 判定を行う。P95 計算、SQL の日付フィルタリングと欠損テーブルに対する保守性も実装。
- パッケージ初期化:
  - kabusys.__init__.py: __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に列挙。

Changed
- （初回リリースため過去変更なし）

Fixed
- （初回リリースため過去修正なし）

Notes / Implementation details
- 環境変数自動ロードはプロジェクトルート探索に依存するため、配布後も CWD に依存しない。.env が見つからない場合は自動ロードをスキップする。
- 設定系では入力検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を厳密に行い、不正値は ValueError を発生させる。
- DB 周りは SQLite および DuckDB に対応。監視用テーブルの初期化は冪等に行われるため複数回呼んでも安全。
- 外部 API（OpenAI など）に依存する機能はフェイルセーフ設計（リトライ、部分スキップ、ログ出力）を重視。
- いくつかの箇所に将来対応の TODO コメントあり（例: position_sizing の銘柄別 lot_size 管理、price のフォールバック戦略）。

開発者向け
- 次回以降のリリースでは、テストケース追加、例外発生時のより詳細なメトリクス報告、並列処理やパフォーマンス最適化（DuckDB クエリ等）を予定。

--- 
（この CHANGELOG はソースコードから推測した機能と設計の要点に基づいて作成しています。）
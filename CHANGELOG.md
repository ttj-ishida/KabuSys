CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし（次回リリースに向けた変更はここに記載されます）


[0.1.0] - 2026-04-17
--------------------

Added
- 初回公開: 基本機能群を実装。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor を定期ポーリングで実行する監視ループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルで安全に終了。
    - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。停止フラグおよび PID 管理に対応。
  - 設定管理
    - config.py: .env 自動読み込み（.env < .env.local を上書き）、.env パーサ（export 形式・クォート・インラインコメント対応）、プロジェクトルート自動検出（.git / pyproject.toml 基準）、Settings クラスによる環境変数集中管理とバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - ツール
    - tools.paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。期間フィルタ、稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL を出力。CLI (--from, --to, --db) に対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定（スコア降順、signal_rank によるタイブレーク）、等金額・スコア加重配分の関数を追加。
    - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、market regime に応じた投下資金乗数 calc_regime_multiplier を実装。
    - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）を実装。単元株丸め、最大ポジション上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ）を考慮した分配ロジックを実装。
  - 研究用モジュール
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実装）。MA200, ATR20, 各種リターン等を計算。
    - research.feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク関数を実装。外部ライブラリ非依存で標準ライブラリのみで実装。
  - AI ニュース NLP（下流処理の骨格）
    - ai.news_nlp: ニュース記事を集約して OpenAI API（gpt-4o-mini）に投げ、銘柄ごとのセンチメント ai_score を計算・書き込む処理フローを実装（ウィンドウ計算、バッチ処理、最大記事/文字数制限、リトライ戦略、応答バリデーション、スコアクリップ、部分更新戦略など）。API キー解決やタイムウィンドウ計算のユーティリティを提供。

Changed
- process priority / CPU 設定ユーティリティを追加・整備（utils.process_priority）。
  - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度を設定。アクセス拒否等は警告でスキップ。
  - set_cpu_affinity: 指定コア数で CPU affinity を設定するユーティリティを追加（失敗時は警告でスキップ）。
- DB 取り扱いの方針
  - 監視（run_monitoring.py）は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db をデフォルト）を使用する設計になっている旨を明記。
  - 実行エンジン（run_execution.py）は paper_trading 環境時に専用 DB を使用して本番 DB と分離。
- config の .env ロード順: OS 環境 > .env.local > .env。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- tools.paper_verification_report のレポート基準と出力フォーマットを整備。欠損テーブル / データ不足時のフォールバック（N/A 表示）を追加。

Fixed
- 各モジュールでの堅牢性向上（推測）
  - portfolio.calc_score_weights: 全銘柄スコアが 0 の場合は等金額配分へフォールバックし WARN ログを出力。
  - portfolio.position_sizing: 価格欠損時のスキップロジック、単元丸めの実装、aggregate cap での端数配分アルゴリズム（残余キャッシュで lot 単位を順に追加）などで安全にゼロ・欠損データを扱うよう改善。
  - research.feature_exploration.calc_forward_returns: horizons の入力検証（正の整数かつ <= 252）を追加して不正引数を防止。
  - research.calc_ic: 有効レコード数が 3 未満なら None を返す等、統計計算の安定化。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行のスキップ等に対応して安全にロード。

Security
- 特記なし。

Deprecated
- 特記なし。

Removed
- 特記なし。

Notes / Breaking changes
- 監視（run_monitoring.py）は「環境にかかわらず」本番 sqlite_path を使う実装（意図的な設計）。Paper Trading で監視を別 DB に切り替えたい場合は注意が必要。
- run_execution は paper_trading 環境で専用 DB を使用するため、paper_trading と本番間で DB スキーマ／データが混在しない設計。ただし運用ルールの周知が必要。

Acknowledgements
- 初期実装段階のため今後の改善点:
  - position_sizing の lot_size を銘柄別に扱う拡張、価格フォールバックロジックの追加（price が欠損時の見積り改善）。
  - ai.news_nlp: OpenAI 呼び出し周りの完全な実装（トランケーション・チャンクング・DB 書き込みの細部）および単体テストの追加。
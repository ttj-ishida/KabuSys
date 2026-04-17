KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
このファイルはコードベース（src/ 以下）から推測して作成しています。

Unreleased
----------

- なし（次回リリースに向けた未リリース変更はここに記載されます）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリースを公開。
- 基本実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時の DB 分離（data/paper_trading.db 等）をサポートし、BrokerClientFactory 経由でブローカクライアントを生成。PID ファイル管理・停止フラグ対応・バックグラウンドスレッドでの実行を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。常に本番 sqlite_path を監視用 DB として使用。
- 設定管理
  - config.py: .env / .env.local の自動ロード機能を実装（プロジェクトルート自動検出）。export 付き行、引用符付き値、インラインコメントの解釈などを考慮した .env パーサを実装。Settings クラスに各種設定プロパティを提供（DB パス、PID/kill フラグパス、閾値、環境種別、PAPER_FILL_MODE バリデーション等）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）および等金額・スコア加重の重み計算（calc_equal_weights、calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームに対するフォールバックと警告を導入。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score）。単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）対応、残差処理による追加配分ロジックを含む。
- リサーチ（ファクター計算・特徴量探索）
  - research/factor_research.py: Momentum, Volatility, Value などのファクター計算を DuckDB クエリで実装。MA200/ATR/出来高/財務指標の取得と計算ロジックを提供。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（スピアマン順位相関）の計算、ファクター統計サマリ（count/mean/std/min/max/median）、ランク計算ユーティリティを実装。外部ライブラリに依存せず標準ライブラリで実装。
  - research.__init__: 提供 API をエクスポート（zscore_normalize 経由の正規化ユーティリティ含む）。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルに書き込むフローを実装。タイムウィンドウ計算、記事トリム（文字数・記事数上限）、バッチ送信、リトライ（429/5xx/タイムアウト等への指数バックオフ）、レスポンス検証、スコアの ±1.0 クリッピング、部分書き換え方式（既存スコア保護）などのフェイルセーフを備える。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定する。コマンドラインオプション --from / --to / --db をサポート。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収し、優先度変更と CPU affinity の設定（set_process_priority, set_cpu_affinity）を提供。権限不足や未対応 OS の場合はログ警告でスキップ。

Changed
- アプリケーション全体の挙動
  - 実行系（run_execution/run_monitoring）起動時にプロセス優先度を最初に "high" に設定するように変更（set_process_priority 呼び出しを導入）。
  - 監視コンポーネント（monitoring）は実行環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様を明記。
  - run_execution は paper_trading 環境で paper_sqlite_path を使用するよう分離（本番 DB と完全分離）。
- .env 読み込みロジック
  - OS 環境変数を保護しつつ .env/.env.local をプロジェクトルートから自動読み込み。override フラグと protected セットによる上書き制御を導入。
  - .env の parsing を強化（export 句・引用符・バックスラッシュエスケープ・インラインコメント取り扱い）。
- ポートフォリオ・ポジション計算
  - aggregate cap 超過時のスケーリング処理を導入し、残差を考慮した lot 単位での追加配分ロジックを実装。
  - price が欠損（0.0 等）の場合の扱い（スキップ）を明示的にログ出力するように変更。
- Research モジュール
  - DuckDB を用いた集計クエリを整理し、ウィンドウ関数で効率的に計算する実装に更新（mobility/ATR/MA の計算における NULL 伝播制御等）。
- AI モジュール
  - OpenAI 連携のための堅牢なバッチ・検証・リトライ戦略を導入。API キー未設定時には明示的に ValueError を送出。

Fixed
- .env 読み込み時のエラーをワーニングとして扱い、読み込み失敗でもプロセス継続するように修正（テストや CI 環境での堅牢性向上）。
- run_execution/run_monitoring の DB 接続後クローズ忘れを防止するため finally ブロックで接続を確実にクローズするように修正。
- factor_research / volatility の true_range 計算で high/low/prev_close のいずれかが NULL の場合に NULL を伝播させる（過小評価を防止）。
- feature_exploration.calc_forward_returns の horizons 入力チェック強化（1..252 の範囲チェック、重複削除）。
- calc_score_weights: 全銘柄スコア合計が 0 の場合に 0 除算を回避して等金額配分へフォールバックするよう修正（警告ログを出力）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で解決し、未設定時は例外を投げて処理を中断するようにしている（無自動フォールバック）。API 呼び出し失敗時のリトライ戦略で特定の transient エラーに対処。

Notes / Known limitations
- position_sizing の price 欠損時の挙動: price_map/open_prices に 0.0 が含まれると当該銘柄はスキップされるため、エクスポージャーの過小見積りが生じ得る（TODO にフォールバック価格導入が記載）。
- news_nlp モジュールの実装ファイル末尾が切れている（提供コードの一部が不完全）。実際の API 呼び出し／DB 書き込み部分の続き実装が必要。
- DuckDB の executemany に関する制約（空パラメータの事前チェック）がコードコメントとして残存。大規模データ挿入時は注意。
- 一部の機能（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）は実装ファイルを参照する設計だが、本 CHANGELOG 作成時点では当該実装の詳細はこの差分からは推測できないため、実装依存の注意事項は別途ドキュメント参照を推奨。

Authors
- このリリースは src/ 以下のコード内容に基づき自動要約して作成しました。

References
- プロジェクトバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を確認。

----------
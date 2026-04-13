Keep a Changelog
================

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

変更履歴は意味のある単位（機能追加・修正など）で記載しています。

v0.1.0 - 2026-04-13
-------------------

Added
- 基本パッケージ初期リリース。
- 実行用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプト。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用して本番 DB と完全に分離。
    - プロセス優先度を開始時に "high" に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用（モニタリング用テーブルの初期化を実行）。
    - プロセス優先度を開始時に "high" に設定。
- 環境設定・読み込み機能（kabusys.config）
  - .env 自動ロードを実装（プロジェクトルートの .git または pyproject.toml を基準に探索）。読み込み優先順は OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを強化: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 環境変数取得ユーティリティ（Settings クラス）を提供。各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
- ポートフォリオ構築機能（kabusys.portfolio）
  - portfolio_builder: シグナルのソート（スコア降順、同点は signal_rank 昇順タイブレーク）、等金額配分、スコア重み配分（全スコア 0 の場合は等分にフォールバック）。
  - risk_adjustment: セクター集中制限 apply_sector_cap（既存保有時価ベースでセクター別エクスポージャー計算、unknown セクターは制限の対象外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）。未知レジームは警告してフォールバック。
  - position_sizing: 複数の配分方式（risk_based, equal, score）に対応した株数計算。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウンと残差に基づく追加配分）を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: DuckDB を使ったモメンタム / ボラティリティ / バリューのファクター計算（prices_daily / raw_financials を参照）。200日移動平均やATR等、欠損データへの頑健な扱いを実装。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず純粋 Python 実装。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0～1.0）を生成して ai_scores テーブルへ書き込む処理を実装。
  - 処理フロー: タイムウィンドウ計算、記事トリミング（最大記事数・文字数）、最大 20 銘柄/チャンクで API コール、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンス検証、スコアクリップ、部分書き換え（対象コードのみ DELETE→INSERT）で部分失敗耐性を確保。
  - OPENAI_API_KEY 未設定時は明示的なエラーを返す。
- ユーティリティ
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。CPU affinity を固定する set_cpu_affinity も実装（None を受け付ける、アクセス権限不足等は警告してスキップ）。
- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95含む）などをまとめる CLI レポートを提供。閾値による PASS/FAIL 判定、--from/--to/--db オプションをサポート。

Changed
- なし（初回リリースのため履歴なし）。

Fixed
- なし（初回リリースのため履歴なし）。

Deprecated
- なし。

Removed
- なし。

Security
- AI スコアリングは外部 API キーを必要とし、api_key 引数または環境変数 OPENAI_API_KEY を必須とする旨を明示。キーが未設定の場合は ValueError を発生させ処理を止める（誤ったキー流出のリスク低減）。

Notes / Breaking changes
- run_monitoring.py は「監視」用に常に Settings.sqlite_path（= 本番監視 DB）を使用します。KABUSYS_ENV の値に関わらず本番 sqlite_path を参照する点に注意してください。
- run_execution.py は paper_trading モード時に paper_trading 用の DB を使用して本番 DB と分離します。paper_trading の挙動（MockBroker の振る舞い）は PAPER_FILL_MODE 等で制御されます。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- いくつかの関数は入力データ不足時に None を返すかログ出力してスキップする挙動になっており、安全に運用できるよう設計されています（例: ファクター計算・レイテンシ集計・position sizing の価格欠損時など）。

開発者向けの補足
- DuckDB と SQLite の両方を利用する設計になっています（時系列ファクター計算は DuckDB、運用監視・トレードログは SQLite）。
- 多くの処理で「欠損データ」「部分失敗」を想定した堅牢化（例外捕捉、ログ出力、フォールバック）が行われています。
- リサーチ・シグナル・ポートフォリオ構築ロジックは純粋関数的に実装されておりユニットテストが容易です（DB 参照なし）。
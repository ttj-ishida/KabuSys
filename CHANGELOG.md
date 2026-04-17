# Changelog

すべての重要な変更をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0 — 初回リリース（2026-04-17）

## [Unreleased]
該当なし。

## [0.1.0] - 2026-04-17

初回公開リリース。自動売買システム KabuSys のコア機能・ユーティリティ群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。ブローカークライアント生成、オーダー管理、リスク管理、Reconciler 組み立て、別スレッドでのセッション実行／停止監視を行う。paper_trading 環境では専用の paper_trading DB を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag を検出して行う。

- 設定管理
  - config.py: プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み実装（.env → .env.local の優先度）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。export 構文、クォート、インラインコメントの取り扱いに対応する .env パーサを実装。
  - Settings クラスを実装し、各種環境変数（データベースパス、API トークン、モード判定、監視しきい値など）をプロパティとして提供。PAPER_FILL_MODE のバリデーションを追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で上位候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア正規化配分を実装（スコア全0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中防止のため候補をフィルタリング。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull/neutral/bear）。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・リスクベース等の方式で銘柄ごとの発注株数を算出。単元丸め、max per-stock 上限、aggregate cap によるスケールダウン（端数処理のため残差配分ロジック含む）、cost_buffer（手数料・スリッページ見積り）対応。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1/3/6 ヶ月リターン、MA200 乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均出来高など。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の算出。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。
    - calc_ic / rank / factor_summary: IC（スピアマン）、ランク変換、列ごとの統計サマリを実装。
  - research パッケージは DuckDB 接続を受け取り、外部 API への依存を持たない設計。

- ニュース NLP（AI スコアリング）
  - ai.news_nlp:
    - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントをスコア化し、ai_scores テーブルへ書き込むためのロジックを開始実装。タイムウィンドウ計算、記事トリミング、バッチ・リトライ、レスポンスバリデーション、スコアクリッピングなどが含まれる。
    - OpenAI API キーの明示的な要求（api_key 引数または OPENAI_API_KEY 環境変数）。429/タイムアウト/5xx に対する指数バックオフ再試行を想定。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX 間の差分を吸収してカレントプロセスの優先度を設定（high/normal/low）。アクセス権限や未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピンニングするユーティリティ（例外時は警告でスキップ）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成する CLI。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）を集計し PASS/FAIL 判定する。閾値（稼働率 99%、成功率 90% 等）を定義し、期間指定（--from/--to）や DB パス指定（--db）に対応。

- DB 初期化補助
  - monitoring.monitoring_db の init_monitoring_db を使用して監視用テーブルの確保（冪等）を run_execution/run_monitoring から呼び出すようにした。

### 変更 (Changed)
- プロセス起動時の挙動
  - run_execution/run_monitoring 起動直後に set_process_priority("high") を実行し、優先度を「高」に設定するようにした（プラットフォームにより効果は異なる）。

- 環境変数読み込みの優先度
  - OS 環境変数を保護しつつ .env/.env.local を読み込む動作を実装（.env.local は上書き可能）。自動ロードの無効化フラグを追加。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応し、不正な行をスキップすることで読み込みの安定性を向上。

- ファクター / リサーチ系の境界条件ハンドリング
  - データ不足時に None を返すようにして downstream での例外発生を回避（例: 移動平均の行数不足、ATR の行数不足、ゼロ除算回避など）。

- position_sizing のスケールダウンロジック
  - aggregate cap によるスケーリングの際に単元（lot_size）を考慮した丸め、残余キャッシュでの追加配分ロジックを実装し、端数処理の安定性を改善。

### 破壊的変更 (Breaking Changes)
- 監視データベースの取り扱い
  - run_monitoring は KABUSYS_ENV に関わらず "本番 sqlite_path"（Settings.sqlite_path）を使用する旨がコードに明示されています。環境に応じた別 DB を期待していた運用では挙動が変わる可能性があります。
- Paper Trading DB の分離
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。既存スクリプトが同一 DB を期待している場合は注意してください。

### ドキュメント / 設定（注意点）
- OpenAI を使ったニューススコアリングは API キーが必須（api_key 引数または OPENAI_API_KEY 環境変数）。
- DuckDB を利用する機能（research、ai.news_nlp 等）が含まれるため、環境に DuckDB が必要です。
- run_* スクリプトは data ディレクトリ内の stop_requested.flag / *.pid ファイルで起動・停止管理を行います。運用時は適切にファイルの配置とアクセス権を管理してください。

---

将来のリリースでは以下のような改善を検討しています（未実装の TODO 等から）:
- position_sizing における銘柄別 lot_size（マスタ参照）対応
- apply_sector_cap の price フォールバック（前日終値や原価）によるエクスポージャー推定改善
- ai.news_nlp のレスポンス処理の完全実装とより細かな失敗時のリカバリ戦略
- 単体テスト・統合テストの追加および CI 統合

--- 

（注）この CHANGELOG は現行コードベースの実装内容から推測して記載しています。運用ポリシーや将来の設計変更により実際のリリースノートは適宜調整してください。
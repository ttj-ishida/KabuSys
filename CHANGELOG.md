# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
主な実装内容はソースコードから推測してまとめたもので、実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- 軽微な改善やドキュメント追記、ログメッセージの微修正など（内部リファクタリングやテスト網羅性向上を想定）。

## [0.1.0] - 初期リリース
最初の公開バージョン。自動売買システム KabuSys のコア機能群を実装しています。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings オブジェクトによる環境変数ベースの設定管理を導入（kabusys.config）。
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き可能）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを提供。
    - 必須環境変数未設定時は明示的なエラーを送出する _require() を実装。
    - 多くのプロパティ（データベースパス、PID パス、監視閾値、環境種別判定等）を提供。

- 実行関連
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - 環境に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時はモックを使用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - ストップフラグ（data/stop_requested.flag）・PID ファイル管理・スレッドによるセッション実行、優先度設定を実装。
    - RiskConfig にデフォルト値を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。

  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は常に本番用 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ検知による優雅な終了、例外キャッチでループ継続するフェイルセーフを実装。

- 監視 / DB
  - monitoring_db 初期化ユーティリティを利用して監視テーブルが存在することを保証。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。
    - フィルタ期間（--from / --to）、DB パス指定 (--db) に対応。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）を採用。
    - DB が存在しない場合のエラーメッセージ出力やテーブル欠如時のフォールバック処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順および signal_rank によるタイブレークで候補を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア比率配分を実装。全スコアが 0 の場合は等金額へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を評価し、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。単元株丸め、per-stock 上限、aggregate cap、cost_buffer（手数料/スリッページ想定）の考慮を実装。
    - リスクベース算出（risk_pct, stop_loss_pct）や lot_size（単元）対応、利用可能現金に応じたスケーリングロジックを実装。

- 研究（research）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR 等、PER/ROE 等）を計算。
    - 長期移動平均や ATR の欠損ハンドリング、カウント閾値による None フォールバック等を実装。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（複数ホライズン同時計算）を取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（ランクは同順位に平均ランクを採用、3 件未満は None）。
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティを実装。
  - research.__init__ で zscore_normalize を data.stats から再エクスポート。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む処理を実装。
    - バッチ処理（最大 20 銘柄）、トークン肥大対策（記事数・文字数トリム）、JSON モード出力を想定。
    - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライ設計、レスポンスバリデーション、スコアの ±1.0 クリップ、部分的な書き換え戦略（DELETE→INSERT で既存スコアを保護）を記載。
    - API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）と未設定時の ValueError。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。権限不足時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定を提供（1 未満は ValueError、権限不足時は警告でスキップ）。

### 変更 (Changed)
- 環境変数ロード
  - .env パーサを堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理の細部（クォートなし時の '#' の取り扱い）を実装。
    - .env と .env.local の読み込み優先度を明確化（OS > .env.local > .env）。
    - 読み込み時に OS 環境変数を protected として上書き防止ロジックを追加。

- 監視・実行起動周り
  - プロセス起動時に最初にプロセス優先度を High に設定する処理を追加（set_process_priority 呼び出し）。
  - DB 接続管理: monitoring は本番 sqlite_path を利用、paper_trading 時は専用 DB を使用するよう分離（安全なテスト運用を想定）。

- ロギング / エラーハンドリング
  - run_monitoring のポーリング内で check_once() が例外を投げても監視ループを継続するようになり、例外時は logger.exception で詳細を出力。
  - run_execution のスレッド管理を改善し、停止フラグ検知時に engine.stop() を呼ぶ仕組みを導入。

### 修正 (Fixed)
- 環境変数パースの不具合回避:
  - MONITOR_POLL_INTERVAL の不正値（0 や負の数、非整数）を検出してデフォルトにフォールバックするように変更（警告ログ出力）。
  - .env 読み込みのファイル I/O エラーは warnings.warn で通知して処理を継続するようにした。

- position_sizing の挙動
  - aggregate cap 適用時の四捨五入 / lot_size 単位での丸め処理、残余分の配分ロジックを実装して利用可能現金超過時のスケーリングを安定化。

### 非機能的改善 (Performance / Reliability)
- DuckDB / SQLite を併用するアーキテクチャを採用し、分析処理（research, ai）とトランザクション系（orders, monitoring）を分離。
- 多くのモジュールで「DB を直接参照しない純粋関数設計」を採用（副作用抑制、テスト容易化）。
- AI API 絡みの処理はフェイルセーフ設計（API 失敗時はスキップして継続）で実運用の堅牢性に配慮。

### 既知の TODO / 注意点
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性がある旨の TODO コメント（フォールバック価格の導入が検討課題）。
- position_sizing の将来的拡張 : 銘柄毎の lot_size を stocks マスタから取得する設計への拡張予定。
- ai.news_nlp は API 呼び出し・レスポンス処理の外部依存（OpenAI）を含むため、API 利用制限や課金に注意。

---

この CHANGELOG はコードの現状（ソースファイル内容）から推測して作成しています。実際のコミットやリリースノートとして使用する場合は、コミットログやリリース時の意図に合わせて適宜修正してください。
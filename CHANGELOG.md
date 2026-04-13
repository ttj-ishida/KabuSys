# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルはコードベース（src/ 以下）から推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-04-13
初回リリース

### 追加
- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
    - RiskManager のデフォルト設定や rate limit / circuit breaker 等のパラメータを実装。
    - ExecutionEngine は DuckDB を分析用途に接続し、pid_file をサポート。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する旨を明示。
    - 起動時にプロセス優先度を上げる処理（set_process_priority）。
    - SQLite / DuckDB の接続確立と監視 DB 初期化処理を含む。

- 設定／環境取扱い
  - config.py: 環境変数管理（Settings クラス）を追加。  
    - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数の保護機能あり）。
    - export KEY=val やクォートやインラインコメントに対応した .env パーサを実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID ファイル等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_DISABLE_AUTO_ENV_LOAD、KILL_FLAG_CLEAR_ON_START 等の環境変数をサポート。

- 監視・監査関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動スクリプトから呼び出し、監視用テーブルが存在することを保証（冪等処理）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（score 降順、signal_rank によるタイブレーク）、等金額・スコア加重の重み計算を実装。
  - portfolio/position_sizing.py: 発注株数の決定ロジック（risk_based / equal / score）を実装。  
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap のスケーリングを実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）および市場レジーム乗数（calc_regime_multiplier）を実装。

- リサーチ・ファクター計算（DuckDB 利用）
  - research/factor_research.py: Momentum, Volatility, Value 等のファクター計算を追加（prices_daily / raw_financials を参照）。  
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe 等を計算。
    - DuckDB SQL を用いたウィンドウ集計の実装。データ不足時は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・rank・統計サマリ（factor_summary）を実装。  
    - ランク計算は同順位を平均ランクにする処理を実装。
  - research/__init__.py: 主要関数のエクスポートを追加。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores テーブルへ書き込む処理を実装。  
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事集約。
    - 1チャンク最大 20 銘柄、記事数/文字数トリム、レスポンスのバリデーション、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（上限付き）。
    - API キーの柔軟な解決（引数または OPENAI_API_KEY 環境変数）と未設定時のエラー。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成コマンドラインツールを追加。  
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を DB（paper_trading.db）から集計してレポート出力。
    - パス指定オプション（--db）、期間指定（--from / --to）対応。閾値基準に基づく PASS/FAIL 判定を出力。
    - P95 の算出、NULL / データ不足時の扱いを考慮。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows と POSIX の差を吸収）と CPU affinity 設定ユーティリティを実装。  
    - Windows 用の HIGH/NORMAL/IDLE マッピング、POSIX 用の nice 値マッピングを実装。
    - 未対応 OS やアクセス権限不足時の安全なフォールバック（警告ログ）を実装。
  - パッケージ初期化等の __init__ ファイルを追加（モジュールのエクスポート整理）。

### 変更
- 監視に関する挙動の明確化
  - run_monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用する旨をコメントで明示（監視データは本番 DB を記録想定）。

- .env 読み込みの挙動
  - OS 環境変数は保護され、.env.local は .env の上書きとして扱う。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を追加。

### 修正（バグ修正 / 安全策）
- .env パーサの堅牢化
  - クォートあり／なし、エスケープ、インラインコメント処理を正しく処理するよう改善。また無効行や export 形式に対応。
- プロセス優先度・CPU affinity の失敗ケースをワーニングで扱い、例外でプロセスを落とさないよう修正。
- position_sizing の資金スケーリング／端数処理において、単元株制約や per-stock 上限を尊重するように実装（安全弁付き）。
- research モジュール・factor 計算はデータ不足時に None を返す等の安全な動作を徹底。
- ai/news_nlp: API キー未設定時は明確な ValueError を送出し、API 呼び出し失敗はリトライとログで安全に扱う。

### ドキュメント（コード内ドキュメント）
- 各モジュールに詳細な docstring を付与。設計方針や注意点（例: ルックアヘッドバイアス回避、DuckDB の executemany 挙動、将来拡張ポイント）を明記。

### 既知の制限 / TODO
- portfolio.position_sizing:
  - price の欠損（0.0）でエクスポージャーが過小見積りされうる旨の注記あり。将来的に前日終値や取得原価のフォールバック導入を検討。
  - lot_size は現状全銘柄共通で固定。銘柄別 lot_map を将来受け取る設計に拡張予定。
- ai/news_nlp: 大量のニュース・多銘柄処理時のトークン上限・コスト管理を更に厳格化する余地あり。
- run_monitoring の監視対象 DB が本番固定である点は運用ポリシーに依存するため注意。

---

今後のリリースでは、ユニットテスト整備、CI 統合、より詳細な運用ドキュメント（デプロイ手順・環境変数一覧）の追加を予定しています。必要であればこの CHANGELOG を英語版にする、または各項目をより細分化して日付ごとの変更ログを追記します。
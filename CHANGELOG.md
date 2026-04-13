# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの現状（src/ 配下の実装）から推測して作成したリリースノートです。

## [0.1.0] - Unreleased
（初期リリース相当のまとめ。パッケージ内の主要機能を網羅しています）

### 追加 (Added)
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理
  - config.py: 環境変数／.env ファイル読み込みユーティリティと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
    - .env および .env.local の読み込み順を実装（OS 環境変数は保護）。
    - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などを考慮した .env パーサを実装。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境判定など）を提供。

- ポートフォリオ構築
  - portfolio_builder.py: 銘柄選定（スコアによるソート）と重み計算（等配分 / スコア加重）。
  - position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元（lot_size）丸め、aggregate cap（スケールダウン）の実装。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。

- 研究（Research）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算関数を実装（DuckDB を利用して prices_daily/raw_financials を参照）。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
  - research パッケージの __init__ で主要 API を公開。

- AI（ニュース NLP）
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事抽出。
    - 銘柄ごとに記事を集約・トリム（記事数上限・文字数上限）。
    - 最大 20 銘柄ずつのバッチ送信、429/ネットワーク/5xx 等は指数バックオフでリトライ、スコアは ±1.0 にクリップ。
    - 出力フォーマットの厳格な検証と DB 書き換えのトランザクション保護（部分失敗時に既存スコアを保護する方針）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成する CLI ツールを追加。
    - 稼働率／注文成功率／送信率／P95 レイテンシ等を集計して判定（PASS/FAIL）する。
    - 日付フィルタ（--from / --to）と DB パス指定オプションを提供。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH により上書き可能）。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS（POSIX 系）差分を吸収して API を提供。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
  - package の __init__.py にバージョン情報（__version__ = "0.1.0"）を追加。

### 変更 (Changed)
- DB 接続の運用方針を明確化
  - 監視プロセス（run_monitoring）は環境に依存せず本番 sqlite_path を参照する設計とした（監視データは本番 DB に保存）。
  - 実行プロセス（run_execution）は paper_trading 環境時に専用 DB を使用し、本番 DB に影響を与えないように分離。

- .env 自動ロードの挙動
  - 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env.local は .env を上書きする形で読み込まれる（ただし OS 環境変数は保護）。

- 複数モジュールでログレベルとエラーハンドリングを強化
  - check_once() の例外を監視ループで捕捉してログ出力しループ継続するようにした（run_monitoring）。
  - DuckDB / SQLite のクエリで OperationalError を捕捉しデフォルト値にフォールバック（ツール系）。

### 修正 (Fixed)
- 環境変数パーサの不具合回避と拡張
  - クォートされた値内のバックスラッシュエスケープを正しく解釈するように改善。
  - export プレフィックスやコメント処理（クォート内はコメントと見なさない等）に対応。

- モニタリングのポーリング間隔検証
  - MONITOR_POLL_INTERVAL の値が 0 以下や不正な文字列の場合、ログに警告を出しデフォルト（60 秒）へフォールバックするように修正（time.sleep に渡す値の安全性確保）。

- ポジションサイズ算出の丸め・スケール処理の安定化
  - 単元（lot_size）での丸め、aggregate cap スケーリング時の再配分アルゴリズム（端数処理）を実装し、合計投資額が利用可能現金を超える場合に安全に縮小するように修正。
  - 価格欠損（None / 0）時はログ出力してスキップするように安定化。

- リスク調整の挙動
  - apply_sector_cap で "unknown" セクターはセクターキャップの対象外とし、既知セクターのエクスポージャー計算から除外する銘柄（売却予定）を考慮するように修正。

- AI ニュース処理の堅牢性向上
  - OpenAI クライアントのエラー系（429, 接続エラー, タイムアウト, 5xx）に対するリトライ処理とログ出力を実装。
  - API キー未設定時に明瞭な ValueError を送出。

### 注意事項 / 既知の制約 (Known issues / Notes)
- DuckDB の executemany の制約により、SQL の一括書き込み前に params が空でないことを確認する実装方針がある（ai/news_nlp コメント等）。
- position_sizing の一部ロジックは将来、銘柄別の lot_size をサポートするために拡張が必要（現状は一律 lot_size:int を想定）。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし、警告ログを出す（意図的なフォールバック動作）。
- ai/news_nlp の処理は OpenAI API への実課金が発生するため、実行時は OPENAI_API_KEY の管理に注意。

---

（将来のリリースでは各項目を細かくバージョン分けして記載してください。必要に応じて Unreleased セクションを分割してリリースノートを作成します。）
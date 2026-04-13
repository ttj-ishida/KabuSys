CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

ルール:
- 変更は可能な限りコードから推測して記載しています。
- 日付はリポジトリから取得できないため記載していません（必要なら追加してください）。

Unreleased
----------
- （未リリースの変更はここに記載）

0.1.0
-----
初回リリース。システム全体の主要コンポーネントを実装。

Added
- 基本パッケージ情報
  - kabusys パッケージの初期バージョンを定義（__version__ = "0.1.0"）。

- 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .git または pyproject.toml を起点にプロジェクトルートを探索して .env を読み込む。
  - export 付き行、クォート文字列（エスケープ対応）、インラインコメントの扱いなどを考慮した .env パーサ実装。
  - OS 環境変数を保護する protected オプション（.env.local の上書き時に OS 環境変数を上書きしない）。
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID ファイル、閾値等）。
  - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live）およびログレベル検証。

- 実行 / 監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - paper_trading モード時は専用の Paper Trading SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（MockBroker を含む想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - duckdb 接続の利用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用してモニタリングデータを一元管理。
    - 起動時にプロセス優先度を "high" に設定。
    - sqlite3 / duckdb 接続を使用、init_monitoring_db を呼んで監視用テーブルの存在を保証。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差異を吸収するプロセス優先度設定ユーティリティを実装。
  - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）に対応。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（引数検証、権限不足時のフォールバックログあり）。
  - アクセス拒否や未サポート機能は警告してスキップする堅牢な実装。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。
    - スコアが全て 0 の場合は等金額配分へフォールバックし警告を出す。
  - risk_adjustment:
    - セクター集中制限を適用する apply_sector_cap（当日売却予定の銘柄を除外可能、"unknown" セクターは制限を適用しない設計）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear を取り扱い、未知レジームは警告してフォールバック）。
  - position_sizing:
    - ポジションサイズ決定 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的見積もり。
    - スケーリング時の端数処理（fractional remainder を用いた再配分）を実装。

- リサーチ（src/kabusys/research/*）
  - factor_research:
    - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクターを DuckDB を使って計算。
    - 欠損データ時は None を返す設計（データ不足に対する安全性）。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - スピアマンランク相関による IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
  - research パッケージのエクスポートを整備（zscore_normalize を含む）。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を実装。
  - 処理フロー: タイムウィンドウ計算（JST ベース→UTC へ変換）、記事集約（1 銘柄あたり記事数・文字数上限）、バッチ送信（最大 20 銘柄/コール）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスのバリデーション、スコアの ±1.0 クリップ、DuckDB への安全な書き込み（部分失敗時に既存スコアを保護する DELETE+INSERT の戦略）。
  - OPENAI API キー未設定時は ValueError を送出。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。
  - コマンドライン引数 --from / --to / --db をサポート。
  - 指標: 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算して PASS/FAIL 判定（閾値はファイル内定義）。
  - DB が存在しない・テーブル欠落時に堅牢に N/A を出力。

Changed
- （初回リリースのため目立った "変更" はなし。今後のリリースで履歴を追加してください）

Fixed
- 環境変数・設定周りの堅牢化:
  - MONITOR_POLL_INTERVAL の不正値（0 以下など）で ValueError を起こさないようフォールバック処理を追加（run_monitoring）。
  - .env パーサでクォート内のバックスラッシュエスケープとインラインコメントを正しく扱うよう実装（config）。

- データ不足時の安全な挙動:
  - ファクター計算やレポート生成でデータが不足する（件数 0 や NULL 値）場合に None／N/A を返すようにして上位処理での例外発生を防止。

Security
- 機密情報の扱い:
  - 環境変数の自動読み込み時に既存の OS 環境変数を保護する仕組みを導入（.env.local による意図しない上書きを防止）。

Notes / Implementation details
- データベース
  - DuckDB と SQLite を併用。prices_daily/raw_financials 等の分析は DuckDB を使用し、稼働監視・トレードログ等は SQLite（data/kabusys.duckdb, data/monitoring.db 等がデフォルトパス）。
  - Monitoring 用テーブルは起動時に init_monitoring_db で冪等的に初期化。

- ロギング
  - 各モジュールで logging を利用。重要なフォールバック時は logger.warning / logger.info / logger.debug を出力。

- フォールバック設計
  - 未知や欠損値に対しては保守的にフォールバック（例: レジーム不明時は multiplier=1.0、全スコア 0 の場合は等金額配分へフォールバック）。

今後の予定（推測）
- 単体テストの追加（特に数値ロジック・スケーリング部分）。
- ブローカー接続周りの実装詳細（MockBroker の具体実装、kabu API クライアント）。
- エラーハンドリングの拡充（AI API の部分での部分成功ロジック、永続化のトランザクション化）。
- モニタリング UI / アラート機能の追加。

補足
- 記載内容はソースコードのコメント・シグネチャ・設計注記から推測してまとめています。運用やリリース履歴と完全に一致しない場合があります。日付やリリース番号の調整、追加の変更点があれば出していただければ更新します。
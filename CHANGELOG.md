# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-12

### 追加
- 新規プロジェクト初版リリース。
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動する CLI ランチャーを追加。
    - KABUSYS_ENV による paper_trading モード対応（MockBrokerClient を利用し、paper_trading 用 SQLite DB へ完全に分離して記録）。
    - プロセス優先度を起動時に設定（utils.process_priority を使用）。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderManager / OrderRepository / Reconciler / RiskManager を組み合わせてエンジンを起動。
    - RiskManager のデフォルト構成（rate limit, circuit breaker, max drawdown 等）を定義。
- 監視エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、duckdb と sqlite を使用。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード（無効化フラグ有り）。
    - .env の柔軟なパーサ実装（export プレフィックス、クォート文字、エスケープ、インラインコメント処理をサポート）。
    - 各種設定プロパティ（DB パス、PID/KILL フラグ、閾値、環境判定など）を提供。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux, Darwin, FreeBSD) をサポート。失敗時は警告でスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等分配・スコア加重）を追加。
  - portfolio/risk_adjustment.py: セクター上限適用と市場レジーム乗数（bull/neutral/bear）を追加。
  - portfolio/position_sizing.py: 株数計算アルゴリズムを追加。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）での丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した安全な再配分ロジックを実装。
- リサーチ（ファクター計算・解析）
  - research/factor_research.py:
    - momentum, volatility, value の各ファクターを DuckDB SQL ベースで実装（prices_daily / raw_financials を参照）。
    - 不足データ時は None を返す設計で安全に動作。
  - research/feature_exploration.py:
    - 将来リターン計算（任意ホライズン）、IC（スピアマン順位相関）、ファクター統計サマリー、rank ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py で主要 API をエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込むモジュールを追加。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
    - 銘柄ごとに記事を集約し、文字数・記事数でトリム（トークン肥大化対策）。
    - バッチ処理（最大 20 銘柄/コール）、JSON Mode 想定、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - レスポンスバリデーション、スコアを ±1.0 にクリップ、部分失敗に対して既存スコアを保護する安全な置換 (DELETE + INSERT の対象コード限定)。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL を判定する閾値付きレポートを標準出力に出力。
    - DB パス指定はコマンドラインオプションまたは環境変数で指定可能。
- その他
  - パッケージ初期化: __init__.py にバージョン __version__ = "0.1.0" を追加。
  - 各モジュールは DuckDB/SQLite を併用する設計（分析用に DuckDB、状態/ログ用に SQLite）。

### 変更
- （初回リリースのため履歴無し）

### 修正 / 注意点
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、コメント認識ルール（クォートなしの場合は '#' の直前が空白かどうかでコメント判断）を実装。
- 環境変数の自動ロードはプロジェクトルートが検出できない場合にスキップする（配布後の CWD 非依存性を考慮）。
- MONITOR_POLL_INTERVAL の入力検証を追加（1 未満の値や非整数はデフォルトにフォールバックし警告）。
- ポートフォリオ/サイズ計算における価格欠損やゼロ除算の扱いを明確化（価格未取得の銘柄はスキップ）。
- CPU/優先度設定やファイル IO 等で権限不足・未対応環境の場合は警告ログを出してスキップするフェイルセーフを実装。

### セキュリティ
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得し、未設定時はエラーを返す（無意識の公開を防止）。

注: 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のリリースノートと差分がある可能性があります。必要であれば特定機能ごとの詳細（API 仕様、設定例、注意点）を追記します。
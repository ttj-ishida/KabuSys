# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。

## [0.1.0] - 2026-04-13
初回リリース。主要機能群（実行エンジン、監視バッチ、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ等）を追加。

### 追加
- 実行エンジン起動スクリプトを追加（run_execution.py）
  - BrokerClientFactory に基づくブローカークライアント生成と ExecutionEngine の起動処理を実装。
  - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite DB を使用して本番データと完全分離（デフォルト: data/paper_trading.db）。
  - プロセス優先度を起動時に High に設定（psutil ベース）。(src/kabusys/run_execution.py)

- 監視ループ起動スクリプトを追加（run_monitoring.py）
  - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
  - 監視用 DB は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。(src/kabusys/run_monitoring.py)

- 環境設定管理（Settings）を追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。OS 環境変数の保護・上書き制御を実装。
  - export 句やクォート・エスケープを考慮した .env パーサ実装。
  - 各種設定プロパティを提供（DB パス、PID/kill flag、閾値、paper_trading 用設定、API トークン取得等）と値検証（列挙型チェックや必須変数チェック）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。(src/kabusys/config.py)

- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/**）
  - 銘柄選定ロジック（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - 数量決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式をサポートし、単元株（lot_size）で丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全側計算を行う。(src/kabusys/portfolio/*)

- リサーチ/ファクター計算モジュールを追加（src/kabusys/research/**）
  - momentum / volatility / value のファクター計算関数を DuckDB SQL で実装（calc_momentum, calc_volatility, calc_value）。
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。外部ライブラリに依存しない純粋な実装。(src/kabusys/research/*)

- ニュース NLP スコアリング（OpenAI）モジュールを追加（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む。
  - バッチ処理（最大 20 銘柄/リクエスト）、文字数・記事数のトリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアのクリッピング等を実装。API キーの未設定ではエラー。（src/kabusys/ai/news_nlp.py）

- 検証用ツール: Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
  - コマンドラインから期間指定で Paper Trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ（P95）などを計算して PASS/FAIL 判定を出力。
  - DB 存在チェックや sqlite の OperationalError に対するフォールバック処理を実装。CLI 引数で DB パスを指定可能。(src/kabusys/tools/paper_verification_report.py)

- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。アクセス権限や未対応 API に対しては警告を出してスキップするフェイルセーフ設計。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。(src/kabusys/utils/process_priority.py)

- パッケージメタデータ
  - パッケージバージョンを 0.1.0 に設定。(src/kabusys/__init__.py)

### 変更（設計上の仕様）
- DB/分析基盤に DuckDB を採用し、ファクター計算・ニュース集約などで DuckDB 接続を使用する設計に統一（各関数は接続を受け取る形）。
- 実行環境（KABUSYS_ENV）に応じて挙動切替（paper_trading と live/development）を明確化。paper_trading は発注系をモック（MockBrokerClient）して DB 分離を行う方針。

### 修正（エラーハンドリング等）
- .env パーサでのクォート／エスケープ処理やインラインコメント解釈を堅牢化。空行・コメント・export 形式に対応。（src/kabusys/config.py）
- MONITOR_POLL_INTERVAL のパースで不正値（0 以下や非整数）を検出した場合にデフォルトにフォールバックして警告を出す実装。（src/kabusys/run_monitoring.py）
- 各種外部操作（プロセス優先度設定、CPU affinity、OpenAI API 呼び出し、SQLite/DuckDB 接続など）で失敗した場合にログ出力して処理を継続するフェイルセーフを多用。

### セキュリティ
- 必須の機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は Settings 経由で取得し、未設定時は ValueError を送出して明確に失敗するようにした。（src/kabusys/config.py）
- OpenAI API キーが未設定のまま news_nlp を呼ぶと ValueError を返す仕様。（src/kabusys/ai/news_nlp.py）

### 既知の注意点 / 制約
- position_sizing の price 欠損時（0.0）はエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格（前日終値や取得原価）を導入することを想定している（TODO コメントあり）。(src/kabusys/portfolio/risk_adjustment.py)
- DuckDB の executemany に関する実装上の注意（空パラメータを渡さない等）が設計メモとして残されている（news_nlp）。(src/kabusys/ai/news_nlp.py)
- ニュース NLP モジュールは外部 API（OpenAI）への依存があり、API の仕様変更や料金・レート制限に影響を受ける可能性がある。

---

今後の予定（例）
- ロギング設定の中央集約（Settings.log_level の導入を実運用に反映）
- 銘柄別 lot_size をマスタ化して position_sizing を拡張
- DuckDB のパフォーマンスチューニング（インデックス・パーティショニング等）
- news_nlp のレスポンス処理の耐障害性強化（部分成功時のロールバック戦略等）

もし特定のファイルの変更点だけを強調したい、もしくは日付・リリース番号の表記を変更したい場合は指示してください。
# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

- ドキュメントポリシー: 追加項目は "Added"、仕様変更は "Changed"、バグ修正は "Fixed"、後方互換性を壊す変更は "Removed" または "Breaking changes"、セキュリティ関連は "Security" に分類します。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-13

初回公開リリース。以下の主要機能・モジュールを実装しています。

### Added
- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動する CLI スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db デフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
  - 注文管理、リスク管理、Reconciler、OrderRepository 等の組み立てを行う。RiskManager のデフォルト構成（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10 等）を定義。
  - 起動時にプロセス優先度を "high" に設定（src/kabusys/utils/process_priority.py を利用）。

- 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
  - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - OS 環境変数を保護するための上書き制御（.env.local は上書き、.env は未設定キーのみ設定）。
  - エントリのパースを強化（export 形式、クォート文字列、インラインコメントの扱い等に対応）。
  - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、paper_trading 用設定、監視しきい値、PID/KILL フラグ等）。
  - 入力値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier。
  - ポジションサイズ決定: calc_position_sizes（リスクベース、等配分、スコア加重に対応。単元株丸め、aggregate cap のスケーリング、cost_buffer 対応）。
  - 全て純粋関数で DB 参照なし（メモリ内計算）。

- 研究・因子計算（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 経由で prices_daily/raw_financials を参照）。
  - 将来リターン・IC・統計要約: calc_forward_returns, calc_ic, factor_summary, rank（外部ライブラリに依存せず実装）。
  - DuckDB を用いた SQL + Python ハイブリッド実装により高速集計を意図。

- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む機能を実装。
  - バッチサイズ、最大記事数 / 文字数トリム、429/5xx/タイムアウト時の指数バックオフリトライ、レスポンス検証、スコアの ±1.0 でのクリップ、部分失敗時に既存データを保護して置換する安全な書き込みを採用。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は例外を送出。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
  - 権限不足等の環境では警告を出して安全にスキップ。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - SQLite の paper_trading DB を参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計してコンソールレポートを出力する CLI を実装。
  - PASS/FAIL の閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）。

- パッケージメタ（src/kabusys/__init__.py）
  - 初期バージョンを __version__ = "0.1.0" として定義。

### Changed
- README 等は本リリースに向けて整備中（コード実装ベースの初期リリース）。

### Fixed
- .env パーサでのクォート / エスケープ / コメント処理を堅牢化し、実運用上の .env 設定ミスに対するフォールバックを実装（src/kabusys/config.py）。
- MONITOR_POLL_INTERVAL の無効値（0 や負値、非整数）に対して警告を出し、デフォルト値へフォールバックするように修正（src/kabusys/run_monitoring.py）。

### Security
- OpenAI API キーや各種シークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は明示的に必須チェックを行う実装を導入。未設定時は ValueError を送出して安全に中断する（src/kabusys/config.py, src/kabusys/ai/news_nlp.py）。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。OS 環境変数は上書き保護されるように実装。

### Notes / Internal
- DuckDB をデータ処理基盤として採用。価格・財務テーブル（prices_daily/raw_financials）を SQL で参照し、ファクター計算や NLP 前処理で活用。
- Execution と Monitoring はプロセス優先度を高めて低レイテンシ実行を意図。
- Paper Trading（検証用）と Live（本番）で DB を分離する設計を採用。Paper 環境ではデータの独立性を確保。

---

今後予定:
- テスト・CI の整備、ドキュメントの充実（使用例・設定例）、エラー監視・アラート連携（LINE 等）の追加を予定しています。
# Changelog

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下の履歴はソースコードから推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔上書き機能の導入。無効な値（0 以下や非整数）は警告を出してデフォルト（60 秒）にフォールバックする実装を追加。
- ニュース NLP スコアリングモジュール（kabusys.ai.news_nlp）を追加。OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎にセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む設計（チャンク送信、トークン肥大対策、リトライ、レスポンス検証、結果クリップなど）。
- Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。system_status、trade_logs、risk_logs などから稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を出力。
- 環境変数読み込みロジックの改善（kabusys.config）:
  - プロジェクトルートの自動検出（.git または pyproject.toml）を実装し、そこから .env/.env.local を読み込む仕組みを追加。
  - .env/.env.local の優先順位（OS 環境 > .env.local > .env）と、OS 側の環境変数を保護する protected キーの取り扱いを導入。
  - export KEY=... 形式やクォート・コメント処理に対応するパーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- 設定（Settings）クラスを追加。アプリケーションで使用する各種設定（DB パス、API トークン、環境モード、監視閾値、paper_trading 用パスなど）をプロパティ経由で取得できるようにした。PAPER_FILL_MODE 等の値検証を実装。
- 実行系起動スクリプト（kabusys.run_execution）を追加:
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離する挙動。
  - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションを実行する流れを実装。
  - 起動時にプロセス優先度を "high" に設定する処理を先頭で実行。
- 監視系起動スクリプト（kabusys.run_monitoring）を追加:
  - SystemMonitor を初期化してポーリングループを回すスクリプトを提供。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 起動時にプロセス優先度を "high" に設定。
- process priority / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加:
  - Windows / POSIX（Linux、macOS、FreeBSD）の差を吸収してプロセス優先度（high/normal/low）を設定。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（アクセス権限や未対応環境では警告を出してスキップ）。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）:
  - 候補選定 & 重み（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - 株数決定・リスク制限・単元丸めロジック（calc_position_sizes）。リスクベース配分、等金額/スコア加重配分、aggregate cap によるスケールダウン処理（小数端数処理と lot_size 単位での再配分）を実装。
- リサーチモジュール（kabusys.research）を追加:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）：DuckDB の prices_daily / raw_financials を参照して複数ファクターを計算（MA200、ATR20、出来高平均、PER/ROE 等）。
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）：将来リターン計算、スピアマンランク相関（IC）の計算、統計サマリー、ランク関数などを実装。外部依存を使用せず標準ライブラリで完結する設計。
- パッケージ初期バージョン情報を追加（kabusys.__init__.__version__ = "0.1.0"）。

### Changed
- DB 接続周りで sqlite3 / duckdb を適切に開閉する設計に統一。監視・実行双方で DuckDB と SQLite の接続を取得・確実にクローズするようになっている（冪等性・リソース解放の強化）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値による time.sleep の例外発生を回避するため、0 以下や非整数は警告してデフォルトにフォールバックする処理を追加。

## [0.1.0] - 2026-04-13

初回リリース（推測） — コア機能セットを実装。

### Added
- コアアーキテクチャ
  - 自動売買システムの基本パッケージ構成（execution / monitoring / portfolio / research / ai / tools 等）。
- 設定管理
  - Settings クラスを提供し、環境変数・.env ファイルからの設定読み込みをサポート。
  - KABUSYS_ENV による環境（development / paper_trading / live）の区別を実装。
- 実行エンジン周り
  - ExecutionEngine 起動スクリプト（run_execution）と関連コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）。
  - Paper Trading 向けに MockBrokerClient を使う分離構成と paper_trading 用 DB の指定。
  - RiskManager の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入。
- 監視
  - SystemMonitor を起動する run_monitoring スクリプトを実装。監視用 DB を初期化する init_monitoring_db を用意。
- データ基盤
  - DuckDB を利用したファクター計算・研究用クエリを実装（prices_daily/raw_financials を前提）。
- ポートフォリオ構築
  - 候補選定、配分重み計算、位置サイズ算出、セクターキャップ、レジーム乗数など PortfolioConstruction に基づく純粋関数群を実装。
- リサーチ & 特徴量
  - モメンタム / ボラティリティ / バリューファクター計算、将来リターン計算、IC 計測、統計サマリー。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ。
- ツール
  - Paper Trading 検証レポート生成ツール（コマンドライン）を実装。

### Security
- 環境変数（API キーやパスワード）の読み込みに際して、OS 側で既に設定されているキーは .env によって上書きされないよう protected により保護する実装を導入。

---

注: 実装の詳細・利用上の注意点は各モジュールの docstring / ソースコード内コメントを参照してください。
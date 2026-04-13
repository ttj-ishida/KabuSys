# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
日付や分類は、ソースコードの実装・ドキュメンテーションから推測して作成しています。

<!-- Unreleased セクション -->
## [Unreleased]

- 今後のリリースで追加予定の改善点（推測）
  - ai/news_nlp.score_news の部分的失敗時の DB トランザクション制御強化
  - position_sizing の銘柄別 lot_size サポート（TODO に記載あり）
  - .env パーサの追加ユニットテスト、Edge-case の更なるカバレッジ

---

## [0.1.0] - 2026-04-13

初回公開リリース。自動売買システム KabuSys のコア機能群を実装しました。以下はソースコードから読み取れる主要な追加・変更点のまとめです。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを実装。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定するユーティリティ呼び出しを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定・環境管理
  - config.py: .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）と詳細な .env パーサを実装。  
    - 優先順位: OS 環境変数 > .env.local > .env。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラス: 各種設定値（DB パス、API トークン、監視閾値、環境種別等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ等を含む。
- モニタリング
  - monitoring_db の初期化呼び出しを各起動スクリプトで保証（冪等に init_monitoring_db を使用）。
- 実行系コンポーネント
  - ExecutionEngine 周りの組立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を起動フローに統合。
  - RiskConfig にデフォルト値を設定し、初期 portfolio value は broker.get_available_cash() を用いる実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等金額配分、スコア加重配分（スコア全0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）。
  - research/feature_exploration.py: 将来リターン計算、IC（スピアマン ρ）計算、ファクター統計サマリー、ランク付けユーティリティ。
  - research パッケージで zscore_normalize を外部（kabusys.data.stats）から再エクスポート。
- AI ニューススコアリング
  - ai/news_nlp.py: OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装。  
    - 銘柄毎に記事を集約してバッチ送信（最大 20 銘柄/チャンク）。  
    - リトライ（429/ネットワーク/5xx 等）を指数バックオフで実施。  
    - スコアは ±1.0 にクリップし、結果を ai_scores テーブルへ書き込む設計（部分置換戦略で既存スコア保護）。
    - タイムウィンドウ計算（JST 基準）やトークン暴発対策（記事数・文字数上限）を備える。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX（Linux, Darwin, FreeBSD）対応でプロセス優先度（nice / HIGH_PRIORITY_CLASS）および CPU affinity 設定関数を実装。  
    - 権限不足や未対応プラットフォーム時には警告を出してフォールバック。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを実装。  
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを計算し PASS/FAIL を判定する閾値を定義。
    - コマンドライン引数 --from/--to/--db をサポート。

### 変更 (Changed)
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加、主要サブパッケージを __all__ で列挙。
- DB 接続ポリシー
  - 監視プロセスは環境に依存せず本番 sqlite_path を使う旨をコード/ドキュメントで明示。
  - ExecutionEngine は paper_trading の場合に専用 SQLite を使用することで本番データと完全分離する設計へ。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメント、空行/コメント行の扱いを詳細に実装。
  - _get_poll_interval()（run_monitoring）: 環境変数が不正な場合にデフォルトへフォールバックし、ログで警告を出すよう実装（time.sleep に負の値を渡さない防御）。
- リソースクリーンアップ
  - 起動スクリプト（run_execution / run_monitoring）で finally ブロックにより sqlite/duckdb コネクションを確実に close する実装。

### 考慮・制約 (Notes)
- News NLP の API キーは環境変数 OPENAI_API_KEY または関数引数で指定が必須。未設定時は ValueError を発生させる設計。
- position_sizing の lot_size は現状グローバル固定で銘柄別対応は TODO（コメントあり）。
- sector_map に存在しない銘柄は "unknown" 扱いになり、apply_sector_cap では上限適用対象外となる（意図的仕様）。
- DuckDB に対する一部の executemany の制約や、欠損データ時の安全な挙動（OperationalError ハンドリング）が各所で考慮されている。

### 既知の改善余地（推測）
- ai/news_nlp のスコア書き込み時にトランザクションや部分失敗リカバリを更に強化するとより堅牢になる可能性。
- .env パーサはかなり包括的だが、より複雑なエスケープや特殊ケースの追加テストで信頼性向上が期待される。
- position_sizing の価格欠損時のフォールバック（前日終値など）の実装注記あり。

---

今後のリリースでは、上記の「Unreleased」に示したような改善や、運用中に見つかるバグ修正・小機能追加が想定されます。必要であれば、各ファイルごとにより詳細な変更点や想定されるリスク・テスト項目のドキュメント化も作成します。
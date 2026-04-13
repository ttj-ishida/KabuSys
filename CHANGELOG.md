Keep a Changelog
=================

すべての注目に値する変更をここに記載します。
このプロジェクトは Keep a Changelog の慣習に沿って管理されています。
Semantic Versioning を使用します。

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- パッケージ初版を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててセッションを実行。  
    - プロセス優先度を起動直後に "high" に設定する処理を追加。
- 監視用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒、無効値は警告してフォールバック）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の設計（監視データを本番監視 DB に集約）。  
    - 起動時にプロセス優先度 "high" を設定。
- 設定管理
  - config.py: 環境変数/.env 自動読み込み機能を追加。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
    - export 付き行、クォート・エスケープ、インラインコメント対応など堅牢な .env パーサを実装。  
    - 必須変数取得用 _require と Settings クラスを提供（J-Quants / kabu / LINE / DB パス /監視設定 /閾値等をプロパティで取得）。  
    - env/log level のバリデーション、paper_trading 用の PAPER_FILL_MODE 検証など。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: シグナル選別と等配分・スコア加重配分を実装（同点タイブレーク等考慮）。  
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。  
    - セクター不明 ("unknown") の扱い、将来的な価格フォールバックの TODO コメントを含む。  
  - portfolio.position_sizing: 発注株数計算 로ジックを実装（risk_based / equal / score の allocation_method、lot_size, cost_buffer, aggregate cap のスケールダウン・再配分ロジック含む）。
  - portfolio パッケージの __all__ エクスポートを整備。
- 実行関連ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity を設定するユーティリティを追加。  
    - サポート外 OS や権限不足時は警告してフォールバックする堅牢な実装。
- 研究/リサーチ機能
  - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB を用いる SQL ベース）を実装。  
    - mom (1m/3m/6m), MA200乖離、ATR20、avg turnover、volume ratio、PER/ROE の取得ロジックを含む。  
    - データ不足時の None ハンドリング、ウィンドウ計算のバッファ付与等を考慮。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。  
    - pandas 等外部依存を避け、標準ライブラリと DuckDB のみで実装。
  - research パッケージは zscore_normalize（data.stats から）を含めてエクスポート。
- AI ニュースNLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込むモジュールを追加。  
    - タイムウィンドウ計算（JST→UTC 変換）、記事の銘柄別集約、1銘柄あたりの文字数・記事数制限、最大 20 銘柄/チャンクでのバッチ送信を実装。  
    - レスポンス検証、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによる 429/ネットワーク/5xx リトライ、部分的な書き込みで既存スコアを保護する戦略（DELETE/INSERT の切り分け）を採用。  
    - API キー未指定時の明示的なエラー、ルックアヘッドバイアス回避の方針（日時参照に注意）。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ指標を集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定を行う。  
    - 日付フィルタ／DB 存在チェック／P95 計算（サンプル列挙）／N/A 表示ロジックを備える。  
    - コマンドライン引数 --from/--to/--db をサポート。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証する処理を run_* スクリプトから実行（冪等）。
- 依存先・DB 接続
  - DuckDB と SQLite を用途に応じて併用する設計を反映（prices / raw_financials 等の分析は DuckDB、監視・発注ログは SQLite）。  

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- （初版のため該当なし）

注記
- 多くのモジュールは「DB 参照なし / 純粋関数」と明記されており、テストやリサーチ用途での再利用を意識した設計になっています。  
- 一部の箇所に TODO コメントや将来的な拡張案（銘柄別 lot_size、価格フォールバック等）が残されています。今後のリリースで機能追加や改善が想定されます。
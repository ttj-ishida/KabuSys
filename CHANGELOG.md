CHANGELOG
=========
(このファイルは Keep a Changelog に準拠しています。セマンティックバージョニングを採用しています。)

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開用の __init__（src/kabusys/__init__.py）を追加し、data/strategy/execution/monitoring モジュールを公開。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定自動読み込み機能を実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
  - .env のパース処理を独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。
  - 必須キー取得時の検査関数 _require を提供（未設定時は ValueError）。
  - 環境（KABUSYS_ENV）およびログレベル（LOG_LEVEL）のバリデーションを実装。
  - デフォルトパス（DuckDB/SQLite）や Slack / kabu API / J-Quants の設定取得プロパティを備えた Settings クラスを提供。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制御（120 req/min 固定間隔スロットリング）を実装する _RateLimiter。
  - リトライロジック（指数バックオフ、最大リトライ回数、429 の Retry-After優先）と 401 発生時の自動トークンリフレッシュに対応。
  - id_token キャッシュを実装しページネーション間で共有。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar と、それらを DuckDB に冪等的に保存する save_* 関数を実装（ON CONFLICT/DO UPDATE を使用）。
  - 入力データの型変換ユーティリティ (_to_float, _to_int) を実装し堅牢性を向上。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集機能（デフォルトで Yahoo Finance カテゴリをサポート）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）による記事 ID の一意化。
  - defusedxml を使った XML パース、受信サイズ制限（10MB）、HTTP/HTTPS スキーム厳格化などによるセキュリティ対策。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING）、news_symbols による銘柄紐付けの想定設計。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離率）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - データ不足時の None 処理、営業日換算のウィンドウバッファ設計等、実務的な欠損対策を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応、SQL で一括取得）、IC（Spearman のρ）計算、ファクターの統計サマリー、ランク付けユーティリティを実装。
    - 外部依存を避け、標準ライブラリ＋DuckDBだけで実行可能な実装方針を明示。
  - 研究 API の再エクスポート（src/kabusys/research/__init__.py）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research で計算した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップを実施。
  - features テーブルへの日付単位の置換（DELETE→Bulk INSERT）で冪等性と原子性を確保。
  - ルックアヘッドバイアス防止の設計方針を明記。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントから最終スコア（final_score）を算出。
  - デフォルト重み・閾値を実装し、ユーザ指定 weights のバリデーション（未知キーの除外、非数値/負値の無視、合計スケール補正）を行う。
  - Sigmoid / 平均化によるスコア正規化、AI スコアの補完（未登録時は中立 0.5）。
  - Bear レジーム判定（ai_scores の regime_score 平均）に基づく BUY 抑制ロジックを実装。
  - エグジット判定（ストップロス -8%、スコア低下）に基づく SELL シグナル生成、SELL 優先のポリシー適用。
  - signals テーブルへの日付単位の置換（トランザクション）で冪等性を保証。

Changed
- ドキュメント・設計注記を各モジュールに追加し、設計方針（ルックアヘッド防止、研究環境の分離、外部 API からの独立性など）を明確化。

Security
- news_collector で defusedxml を採用し XML ベースの攻撃（XML Bomb 等）を軽減。
- RSS の受信サイズ制限と URL スキームチェックによりメモリ DoS / SSRF リスクを低減。
- J-Quants クライアントでのトークン自動リフレッシュと限定された再試行により認証周りの堅牢性を向上。

Performance
- J-Quants API のページネーション処理とトークンキャッシュで大量データ取得時のオーバーヘッドを低減。
- DuckDB 側でウィンドウ関数や一括 INSERT を活用し、集計/バルク処理の効率を確保。

Fixed
- 多数の None / 非有限値処理（math.isfinite の使用）、PK 欠損行のスキップ、例外時のトランザクションロールバック処理を実装して実行時の堅牢性を改善。

Notes / Known limitations
- research モジュール・feature_engineering は "ルックアヘッドを避ける" 設計だが、positions テーブルに peak_price や entry_date が無い場合はトレーリングストップや時間決済など一部のエグジット条件は未実装（コード内に注記あり）。
- execution モジュールはパッケージに存在するが本差分では実装の詳細が含まれていない（将来的な実装・統合が予定される）。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は参照されているが本差分での実装ファイルは省略されている可能性あり。

Breaking Changes
- なし（初期リリースのため該当なし）。

注記
- 各関数・モジュールに設計方針や処理フローの docstring を充実させ、コードの自己説明性を高めています。運用時は .env.example を参照して必須環境変数を設定してください（Settings._require により未設定時は ValueError になります）。
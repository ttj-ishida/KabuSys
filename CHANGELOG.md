# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、意味のある変更のみを記載しています。

次のバージョン履歴は、リポジトリ内のソースコードから推測して作成しています。

## [0.1.0] - 2026-03-20

初回リリース — 基本的なデータ取得・前処理・ファクター計算・シグナル生成のコア機能を実装。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。公開 API として data/strategy/execution/monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順（OS 環境変数 > .env.local > .env）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - シェル形式の export KEY=val、クォートやエスケープ、インラインコメントの扱いなどを考慮した .env パーサを実装。
  - Settings クラスにてアプリケーション設定をプロパティで提供（J-Quants トークン、kabuAPI パスワード、Slack トークン/チャンネル、DB パス、環境 (KABUSYS_ENV)、ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（不正値で ValueError を送出）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限制御（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して再リクエスト（1 回のみ）。
  - ページネーション対応で daily_quotes / statements / trading_calendar を取得する fetch_* 関数を実装。
  - DuckDB への保存用 save_* 関数を実装（raw_prices / raw_financials / market_calendar）。ON CONFLICT を使った冪等保存をサポート。
  - 取得データの型変換ユーティリティ (_to_float / _to_int) を実装し、無効データを安全に扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news 等へ保存する機能を実装（デフォルトで Yahoo Finance のビジネス RSS をサポート）。
  - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）などのセキュリティ対策を実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - 記事 ID は URL 正規化後のハッシュで冪等性を確保する方針（コメントで明示）。
  - DB バルク挿入のチャンク化・トランザクション単位での保存処理により効率的かつ安全に保存。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装。
    - prices_daily / raw_financials テーブルのみ参照する純粋な計算ロジック。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（複数ホライズン、lead ウィンドウを用いた高性能 SQL 実装）。
    - IC（Spearman の ρ）計算（ランク化、同率順位は平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median）や rank ユーティリティ。
  - 研究用 API を __init__ でエクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールが出す raw ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定列に対する Z スコア正規化、±3 でのクリップを実行。
  - features テーブルへの日付単位の置換（DELETE → bulk INSERT）をトランザクションで行い冪等性を確保。
  - ルックアヘッドバイアス対策に「target_date 時点のデータのみを利用」する設計を採用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
  - 各コンポーネントの計算関数とシグモイド変換／欠損補完ロジックを実装。
  - デフォルト重みを持ち、ユーザ渡し weights を検証・正規化（不正値は無視、合計が 1 に再スケール）。
  - Bear レジーム検知（ai_scores の regime_score 平均が負の場合、一定サンプル数が必要）による BUY 抑制。
  - BUY 閾値（デフォルト 0.60）以上で BUY シグナル生成、既存ポジションに対するエグジット判定（ストップロス -8%、スコア低下）で SELL シグナル生成。
  - signals テーブルへの日付単位置換をトランザクションで実行し冪等性を確保。
  - SELL が優先されるポリシーを実装（SELL 対象は BUY から除外）。

- パッケージの公開 API (kabusys.strategy.__init__)
  - build_features / generate_signals をエクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 攻撃から保護。
- ニュース収集で受信最大サイズを設定しメモリ DoS を軽減。
- J-Quants クライアントでトークンリフレッシュ時の無限再帰を防止するフラグを導入。
- 外部 URL パース時の正規化とトラッキングパラメータ除去により ID 一意化の信頼性を向上。

### 既知の制限・未実装 (Known issues / Not implemented)
- signal_generator のエグジット条件でコメントとして挙げられている「トレーリングストップ（peak_price に依存）」「時間決済（保有 60 営業日超過）」は未実装。positions テーブル側の拡張が必要。
- news_collector の記事 ID 生成や銘柄紐付け（news_symbols）などは仕様で言及されているが、実装の一部がコメントベースで設計方針として残っている可能性あり。
- execution / monitoring パッケージは最小限の骨組み（もしくは空）で、発注実行や監視インテグレーションの実装が必要。

### マイグレーション / 注意事項 (Migration notes)
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が Settings により必須として参照されるため、本番利用前に .env を整備してください。
- DuckDB / SQLite のデフォルトパスは settings にハードコードされた既定値があるため、必要に応じて DUCKDB_PATH / SQLITE_PATH を設定してください。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後に意図しない自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。追加のコミット履歴やリリースノートが存在する場合は、そちらを優先して正確な変更履歴を反映してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-20

最初の公開リリース。日本株自動売買システムのコアライブラリ群を実装しました。  
主要コンポーネントはデータ取得・永続化、研究用ファクター計算、特徴量生成、シグナル生成、設定管理、ニュース収集などです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期実装。公開 API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（execution はプレースホルダ）。
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（読み込み順: OS 環境 > .env.local > .env）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 高度な .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォートとエスケープ対応、インラインコメント処理などをサポート。
  - 必須環境変数取得のための Settings クラスを提供。要求される主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV（development/paper_trading/live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - API レート制限対応（120 req/min）: 固定間隔スロットリングによる RateLimiter。
    - 冪等な保存ロジック: DuckDB への INSERT … ON CONFLICT DO UPDATE を使用。
    - リトライロジック（指数バックオフ、最大 3 回）および 401 の自動トークンリフレッシュ。
    - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - DuckDB へ保存する save_* 関数（raw_prices / raw_financials / market_calendar）。
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換処理）。
    - データ取得時の fetched_at は UTC で記録（Look-ahead バイアス対策）。

- 研究・ファクター計算 (kabusys.research)
  - ファクター計算関数:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR・流動性系）
    - calc_value: per / roe（raw_financials と prices_daily を組み合わせ）
  - 解析ユーティリティ:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一クエリで取得
    - calc_ic: スピアマンランク相関 (IC) 計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理（丸めにより ties を安定化）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 関数:
    - research の生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 正規化: 指定列に対して Z スコア正規化（kabusys.data.stats を利用）を実施し ±3 でクリップ。
    - 日付単位で冪等に features テーブルへ UPSERT（削除→挿入のトランザクション）を実施。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 関数:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news を重み付き合算して final_score を算出。
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60）。
    - AI レジームスコア群の平均から Bear 判定を行い、Bear 時は BUY を抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）を実装。
    - signals テーブルへ日付単位で置換（冪等な DELETE→INSERT トランザクション）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集と raw_news への保存（冪等）:
    - デフォルト RSS ソースに Yahoo Business を設定。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で一意化。
    - defusedxml による XML パースでセキュリティ対策（XML Bomb 等）。
    - 受信サイズ制限（10MB）や不正スキーマの排除、SSRF 対策を考慮。
    - バルク INSERT のチャンク処理で効率的に保存。

### 変更 (Changed)
- （初版のため過去の変更はありません）

### 修正 (Fixed)
- （初版のため過去の修正はありません）

### 既知の制限 / 注意点 (Known issues / Notes)
- Signal の一部条件は未実装:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有日数ベースの決済）
  これらは positions テーブルに peak_price / entry_date 等の追加が必要です（注釈あり）。
- feature_engineering 内で avg_turnover はフィルタにのみ使用し、features テーブルには保存していません（コメント参照）。
- research モジュールは DuckDB の prices_daily / raw_financials のみを参照し、外部 API 呼び出しは行いません。
- 実行（execution）層はこのリリースで発注 API への統合を持たないため、本番注文の送信ロジックは別途実装が必要です。
- .env 自動ロードはプロジェクトルート検出に .git または pyproject.toml を使用するため、配布形態によっては期待通りに動作しない場合があります。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか明示的に環境変数を設定してください。
- calc_forward_returns の horizons は 1〜252 日の範囲であることを要求します（検証あり）。
- 数学的な計算では NaN/Inf の取り扱いに注意しており、無効値は None として扱われます。

### セキュリティ (Security)
- news_collector で defusedxml を使用し、最大応答サイズ制限・HTTP スキーム検査など SSRF / XML Bomb 対策を導入。
- jquants_client は 401 発生時にトークン自動リフレッシュを行うが、リフレッシュ失敗時には明示的な例外を発生させます。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 必要な DB テーブル（例）:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news
  - スキーマは各モジュールの INSERT/SELECT に依存するため、事前に適切なスキーマを用意してください。
- 必須環境変数を設定してください。開発中は .env/.env.local をプロジェクトルートに配置して利用できます。
- J-Quants API を利用するには JQUANTS_REFRESH_TOKEN を設定してください。get_id_token の呼び出しでトークンを取得します。
- ログレベルは LOG_LEVEL で制御できます。KABUSYS_ENV によって is_live/is_paper/is_dev が判定されます。

---

今後の予定（予定項目）
- execution 層: signals を元に実際に発注を行うモジュールの実装
- positions テーブル拡張: peak_price / entry_date 等を保存してトレーリングストップや時間決済を実装
- ai_scores の生成パイプライン（外部 NLP/モデル統合）
- テストカバレッジと CI の拡充

---- 

開発に関する詳細や設計ドキュメントはリポジトリ内の StrategyModel.md / DataPlatform.md / research ディレクトリ内の docstring を参照してください。
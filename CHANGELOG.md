# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のコードベースから機能・設計を推測して作成しています。

## [0.1.0] - 2026-03-19

### 追加
- パッケージ初期リリース: KabuSys - 日本株自動売買システム（version 0.1.0）。
- モジュール構成:
  - kabusys.config:
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml を基準に探索）。
    - .env のパース実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ、行内コメント処理を考慮）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 環境変数必須チェック用の _require() と Settings クラスを実装。以下の必須設定プロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 設定の検証: KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション。
    - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db を提供。

  - kabusys.data.jquants_client:
    - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限管理（120 req/min）を RateLimiter で実装。
    - HTTP リクエストの汎用処理 _request を実装（JSON パース、タイムアウト、ページネーション対応）。
    - 再試行（指数バックオフ）、Retry-After の処理、特定ステータスコード（408/429/5xx）でのリトライロジックを実装。
    - 401 応答時にリフレッシュトークンを使って id_token を自動更新して 1 回リトライする仕組みを実装（get_id_token / _get_cached_token）。
    - ページネーション対応のデータ取得: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
    - DuckDB 保存用の冪等化関数: save_daily_quotes, save_financial_statements, save_market_calendar を実装（ON CONFLICT DO UPDATE で重複排除）。
    - 取得データの型変換ユーティリティ: _to_float, _to_int。
    - fetched_at を UTC ISO 形式（Z）で記録し、データ取得時刻をトレース可能に。

  - kabusys.data.news_collector:
    - RSS ニュース収集モジュールを追加（RSS 取得・正規化・DB 保存の下地）。
    - URL 正規化処理を実装（クエリのトラッキングパラメータ除去、キーソート、スキーム/ホスト小文字化、フラグメント除去）。
    - メモリ DoS を防ぐための受信最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）。
    - defusedxml を用いた XML パース想定（攻撃対策）。デフォルト RSS ソース辞書を用意（例: Yahoo Finance）。
    - バルク INSERT 用のチャンクサイズ設定、記事 ID をハッシュで生成する方針（説明あり）。

  - kabusys.research:
    - 研究目的の解析モジュールを実装。
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する関数。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算する関数（tie の平均ランク対応、最小サンプル判定）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクを返すランク関数（浮動小数丸めによる ties 対応）。

  - kabusys.research.factor_research:
    - ファクター計算関数を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）の計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover（20日平均売買代金）, volume_ratio（当日 / 20日平均）を計算。
    - calc_value: target_date 以前の最新財務データを結合して per, roe を計算（EPS が 0/欠損時は None）。

  - kabusys.strategy.feature_engineering:
    - 研究で算出した生ファクターを統合・正規化して features テーブルへ保存する機能を実装（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - 正規化対象列の Z スコア正規化と ±3 でのクリップを適用（zscore_normalize を利用）。
    - DuckDB トランザクションで日付単位の置換（DELETE→INSERT）を行い冪等性を保証。

  - kabusys.strategy.signal_generator:
    - features と ai_scores を統合して最終スコアを算出し、BUY / SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算ロジックを実装（シグモイド変換、欠損は中立 0.5 で補完）。
    - デフォルト重みとしきい値を定義（デフォルト threshold=0.60、weights の補完・再スケール処理を実装）。
    - AI レジームスコアを集計して Bear 相場判定を実装（サンプル不足時の扱いを明確化）。
    - SELL（エグジット）条件のうちストップロス（-8%）とスコア低下を判定する機能を実装（positions / prices_daily を参照）。
    - signals テーブルへ日付単位の置換を行い冪等性を保証。

- パッケージの public API:
  - kabusys.__all__ に data/strategy/execution/monitoring を含めた公開構成。
  - kabusys.research に主要関数を __all__ にてエクスポート。

### 変更
- 初回リリースのための設計文書参照（コメント内に StrategyModel.md / DataPlatform.md など参照を記載）により、実装が仕様に準拠することを明示。

### セキュリティ
- news_collector は defusedxml を用いて XML パースを行う想定で XML Bomb 等の攻撃緩和を考慮。
- news_collector 側で受信サイズを制限することでメモリ DoS を軽減。
- jquants_client ではトークン自動リフレッシュとレート制限を組み合わせて API 利用の安全性および健全性を確保。

### 既知の制限（ドキュメント化）
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済等）は positions テーブルに追加情報（peak_price / entry_date 等）が必要で、現バージョンでは未実装。
- news_collector の完全な RSS 取得・記事分解ロジックは骨子（URL 正規化・パース・セキュリティ方針）を実装しているが、外部フェッチや DB への紐付け処理の詳細は今後の拡張想定。
- 一部処理は DuckDB のテーブル定義（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）に依存するため、使用前に該当スキーマを準備する必要あり。

---

今後のリリースでは以下を優先的に検討してください:
- news_collector の完全実装（記事 ID 生成、記事テキスト正規化、news_symbols との紐付け、DB INSERT RETURNING の採用）。
- positions テーブルの拡張（peak_price / entry_date）およびトレーリングストップ等の追加エグジットルール。
- execution 層（kabu API 連携）と monitoring（Slack 通知等）の実装と統合テスト。
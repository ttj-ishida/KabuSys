CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

- （なし）


[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース: KabuSys 0.1.0 を公開。
- パッケージ構成:
  - kabusys.config
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 独自の .env パーサ実装（コメント行、export プレフィックス、クォート内のエスケープ処理、インラインコメント処理などに対応）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB 等の設定プロパティ（必須キー取得時は例外を投げる）。
    - 環境値検証（KABUSYS_ENV/LOG_LEVEL のバリデーション）と利便性プロパティ（is_live / is_paper / is_dev）。
  - kabusys.data.jquants_client
    - J-Quants API クライアント実装（ページネーション対応）。
    - レートリミッタ（120 req/min 固定間隔スロットリング）を実装し API 呼び出し間隔を制御。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After ヘッダ優先。
    - 401 response 時は自動でトークンをリフレッシュして 1 回リトライ（無限再帰を防止）。
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（冪等性を ON CONFLICT により確保）。
    - 型安全な変換ユーティリティ (_to_float / _to_int) と fetched_at の UTC 記録。
  - kabusys.data.news_collector
    - RSS ベースのニュース収集モジュール（記事正規化・トラッキングパラメータ除去・ID ハッシュ生成等を設計）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）、トラッキングパラメータ除去／URL 正規化ロジックなどセキュリティ＆堅牢性考慮。
    - raw_news への冪等保存を想定（バルク挿入／チャンク化）。
  - kabusys.research
    - ファクター計算モジュール（factor_research）:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR の NULL 伝播制御あり）。
      - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算（最新財務レコードを取得）。
    - 特徴量探索モジュール（feature_exploration）:
      - calc_forward_returns: 任意ホライズンの将来リターンを一度に取得（パフォーマンスのためスキャン範囲を制限）。
      - calc_ic: スピアマンのランク相関（IC）を計算（ties の平均ランク処理）。
      - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
    - いずれの関数も DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（外部 API へはアクセスしない設計）。
  - kabusys.strategy
    - feature_engineering.build_features:
      - research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
      - 正規化（zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性確保）。
      - 欠損や価格取得ロジックは休場日対応（target_date 以前の最新価格を参照）。
    - signal_generator.generate_signals:
      - features と ai_scores を統合しコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
      - 重み付け合算で final_score を算出。weights の検証・補完・正規化に対応（既定値: momentum 40% 等）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制）、閾値による BUY シグナル生成（デフォルト閾値 0.60）。
      - SELL シグナル（エグジット）判定を実装（ストップロス -8%、final_score の閾値未満）。未実装の条件（トレーリングストップ、時間決済）は注記あり。
      - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性）。
      - 生成処理は発注層に依存せず DB（DuckDB）を参照するのみ。
  - パッケージ初期化
    - kabusys.__init__ により主要サブパッケージを __all__ で公開。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / Limitations
- 一部アルゴリズムや条件は README/ドキュメントに基づく仕様に沿って実装されているが、将来的に調整が必要（例: 戦略モデルの重み・閾値）。
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は positions テーブルに追跡情報（peak_price / entry_date 等）が追加されれば実装可能と記載。
- news_collector の実装は設計部分が含まれているが、RSS パース／DB 連携の詳細実体（insert ロジックなど）は引き続き実装・検証が必要な箇所がある可能性あり。
- すべての外部 API 呼び出しはレート制御・リトライ・トークン管理を行う設計だが、本番環境での大規模運用時はさらに監視・メトリクスが推奨。

Required environment variables (例)
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH / SQLITE_PATH（デフォルトの格納先あり）

以上。ご要望があればリリースノートの英語版や、各モジュールごとの詳細なリファレンス（入力/出力スキーマや例）も作成します。
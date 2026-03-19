# Changelog

すべての変更は Keep a Changelog の規約に準拠しています。  
安定版リリース以外は "Unreleased" に記載します。

## [Unreleased]
- 

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリを追加。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本構成を追加。__version__ = 0.1.0、公開モジュールとして data / strategy / execution / monitoring を定義。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境 > .env.local > .env。テスト等で無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント行、export プレフィックス、クォート／エスケープ処理、インラインコメント処理を考慮）。
  - 必須環境変数の取得ヘルパー _require と、よく使う設定項目をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live）, LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - env の検証（有効な値チェック）と is_live / is_paper / is_dev の便利プロパティを提供。

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（固定間隔スロットリング、デフォルト 120 req/min）を RateLimiter で制御。
  - 再試行ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx に対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンから ID トークンを自動取得して 1 回だけリトライする仕組みを実装（トークンキャッシュ共有）。
  - ページネーション対応で日足・財務データ・マーケットカレンダーを取得する fetch_* 関数を提供。
  - DuckDB へ冪等保存する save_* 関数を実装:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - 数値変換ユーティリティ _to_float / _to_int を実装（安全な None 返却、"1.0" などの扱いなど）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する機能を追加。
  - URL 正規化（スキーム/ホストを小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - 記事 ID は正規化後 URL の SHA-256（先頭 32 文字）を用いる方針（冪等性確保）。
  - セキュリティ対策: defusedxml を使用して XML 攻撃に備える、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設置、SSRF 想定の URL チェック等（設計に明記）。
  - バルク INSERT のチャンク処理や INSERT RETURNING を想定した設計（パフォーマンス配慮）。

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research モジュールにてファクター計算を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR / atr_pct / avg_turnover / volume_ratio を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を算出（EPS が 0 または欠損の際は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（LEAD を使用）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算（有効レコード 3 未満は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank ユーティリティ（同順位は平均ランク、round(v,12) による ties の防止）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで算出した生ファクターを集約・正規化して features テーブルに保存する build_features を実装。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value から取得
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定列で Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - 日付単位で DELETE->INSERT を行い冪等性を確保（トランザクション）
  - 欠損・非数値への扱いや休場日・当日欠損に対応した直近価格参照ロジックを実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する generate_signals を実装。
  - 特徴:
    - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10（ユーザ指定 weights は検証・正規化して受け付ける）
    - シグモイド変換やコンポーネントスコアの欠損補完（中立 0.5）によりロバストなスコア計算
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、サンプル数閾値あり）による BUY 抑制
    - エグジット条件（ストップロス -8%、スコア低下）に基づく SELL シグナル生成（価格欠損時の判定スキップ等の安全措置あり）
    - BUY / SELL を日付単位で DELETE->INSERT（トランザクション）して冪等性を確保
    - signals テーブルへの挿入において SELL が優先されるポリシー（BUY から除外、ランク再付与）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用するなど XML 関連の脆弱性対策を明示。
- J-Quants クライアントでのトークン自動リフレッシュは無限再帰を避けるため allow_refresh フラグで制御。

### 既知の制限 / 今後の実装予定
- signal_generator の一部のエグジット条件（トレーリングストップ・時間決済）は positions テーブルに peak_price / entry_date 等の列が必要であり現状未実装（doc に明記）。
- news_collector の RSS パースや SSRF 防止の詳細な実装は設計に記載されているが、実装の追加整備・テストが必要。
- execution（発注）層はパッケージ構造には用意されているが、本リリースでは発注 API への直接の統合は行わない設計。

---

[0.1.0]: https://example.com/release/0.1.0 (初回リリース)
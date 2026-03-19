Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

フォーマット:
- すべての変更はセマンティックバージョニングに従います。
- 各リリースには「Added / Changed / Fixed / Security / Removed / Deprecated / Notes」などのセクションを用います。

[0.1.0] - 2026-03-19
-------------------

Added
- 初回公開リリース。kabusys パッケージの基礎機能を実装。
- パッケージ初期化
  - src/kabusys/__init__.py: バージョン定義 (__version__ = "0.1.0") と主要サブパッケージの公開 (data, strategy, execution, monitoring) を追加。

- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env および .env.local をプロジェクトルートから自動読み込みする仕組みを実装（.git または pyproject.toml を基準にルート検出）。
    - export KEY=val 形式、クォート付き値、インラインコメントなどを考慮した堅牢な .env パーサーを実装。
    - OS 環境変数を保護するための上書き制御（override / protected）を導入。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供。必須キー:
      - JQUANTS_REFRESH_TOKEN
      - KABU_API_PASSWORD
      - SLACK_BOT_TOKEN
      - SLACK_CHANNEL_ID
    - デフォルト値:
      - KABUSYS_ENV: "development"
      - LOG_LEVEL: "INFO"
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
    - env 値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- Data 層 (J-Quants 統合・ニュース収集)
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。機能:
      - ID トークン取得（refresh token からの auth_refresh）。
      - ページネーション対応で日足・財務・マーケットカレンダーを取得する fetch_* 関数。
      - 固定間隔スロットリングによるレート制限 (_RateLimiter、120 req/min)。
      - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ、429 の Retry-After 優先）。
      - 401 時は自動でトークンリフレッシュして 1 回リトライ。
      - 取得時刻（fetched_at）を UTC ISO8601 形式で付与して Look-ahead バイアス追跡を可能に。
      - DuckDB 保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等性を確保（ON CONFLICT DO UPDATE）。
      - 入力値変換ユーティリティ (_to_float / _to_int) を実装し、無効値を安全に扱う。

  - src/kabusys/data/news_collector.py:
    - RSS フィードからニュース記事を収集・正規化して raw_news に保存する設計を実装（記事モデル、URL 正規化ユーティリティなど）。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成する方針を採用し冪等性を保証。
    - defusedxml を利用して XML 関連の攻撃（XML Bomb 等）に対処。
    - 受信サイズ上限（10MB）やトラッキングパラメータ除去、クエリパラメータソートなどの正規化ロジックを実装。
    - バルク INSERT のチャンク化や INSERT RETURNING を想定した効率的な DB 保存方針。

- Research 層（因子計算・探索）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value（PER, ROE など）関連のファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA の可用性チェック含む）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range 計算で NULL 伝播を正しく扱う）
      - calc_value: PER（EPS が 0 または欠損なら None）と ROE（raw_financials から最新財務を取得）
    - DuckDB 上で SQL を用いた効率的なウィンドウ集計を採用し、営業日の欠損や範囲バッファ（カレンダー日バッファ）を考慮。

  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用、ホライズン検証あり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。ペア数が 3 未満の場合は None を返す。
    - rank / factor_summary: 同順位処理（平均ランク）を考慮したランク化関数と、count/mean/std/min/max/median の統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。

  - src/kabusys/research/__init__.py: 主要 API を再エクスポート。

- Strategy 層（特徴量整形・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py:
    - 研究用の生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + DELETE/INSERT による冪等処理）を実装。
    - ルックアヘッドバイアス回避の設計を明示。

  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントスコア変換: Z スコア → シグモイド変換、PER からのバリュー計算等を実装。
    - 最終スコア final_score を重み付き合算（デフォルト重みを定義）し、BUY/SELL シグナルを生成。
    - Bear レジーム判定（ai_scores の regime_score を平均し負なら Bear。ただしサンプル数閾値あり）。
    - SELL 判定にはストップロス（-8%）とスコア低下を実装。トレーリングストップや時間決済は未実装で仕様上の注記あり。
    - signals テーブルへの日付単位置換（トランザクション + DELETE/INSERT）で冪等処理。
    - weights 引数の検証・スケーリング、無効値スキップ、合計が 1.0 でない場合の再スケール処理を実装。

- パッケージ構成のエクスポート
  - src/kabusys/strategy/__init__.py: build_features / generate_signals を公開。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- RSS パーシングに defusedxml を使用して XML に起因する攻撃を緩和。
- news_collector で受信サイズを 10MB に制限、悪意ある大容量応答による DoS を軽減。
- J-Quants クライアントでトークンを明示的にリフレッシュし、401 の取り扱いを安全に実装。

Notes / Known limitations
- execution と monitoring サブパッケージはこのリリースでは機能が限定的（executionパッケージは空の __init__）。発注 API との接続・実行層は別途実装予定。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
- calc_value は PBR や配当利回りなど一部バリューファクターを未実装。
- news_collector の URL/SSRF 対策は設計に含むが、外部からの URL 入力経路に応じた追加対策（DNS/IP 制限など）が必要な場合がある。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など）は本 changelog に含まれないため、運用前に DB スキーマ整備が必要。

Upgrade / Migration notes
- 環境変数の設定:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトパスは DUCKDB_PATH / SQLITE_PATH を使用するが、運用環境に合わせて環境変数で上書き可能。
  - 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB へデータを投入する前に必要なテーブルを作成してください（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など）。SQL スキーマはリポジトリの別箇所またはドキュメント参照。

依存関係（主なもの）
- duckdb
- defusedxml
- 標準ライブラリ urllib / datetime 等

貢献者
- 初回実装（単一コードベース提供） — 実装者によるコミット。

お問い合わせ
- バグ報告・改善提案は issue を作成してください。具体的な再現手順・ログ・環境情報を添えていただけると対応が早くなります。

(注) 本 CHANGELOG は提供されたコード内容から推測して作成しています。実際のコミット履歴やドキュメントに基づく詳細はリポジトリの履歴/README をご参照ください。
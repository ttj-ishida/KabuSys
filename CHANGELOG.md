# Changelog

すべての注目すべき変更をここに記載します。  
このファイルは「Keep a Changelog」フォーマットに従い、セマンティックバージョニングを採用します。

## [Unreleased]


## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。以下はこのバージョンで追加された主要な機能・設計上のポイントのまとめです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名・バージョン（0.1.0）と公開モジュール一覧を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装（コメント・export 前置・シングル/ダブルクォート・エスケープ対応、インラインコメントルール）。
  - 読み込み時の保護（既存 OS 環境変数は protected として上書き抑止）をサポート。
  - 必須設定の検証 (_require) と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須変数。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH 等の既定値。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（認証・ページネーション・取得・保存）。
  - レート制限管理: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大試行回数、特定ステータス（408, 429, 5xx）での再試行。
  - 401 発生時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避）。
  - JSON レスポンスデコードのエラーハンドリング。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存関数:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - fetched_at を UTC ISO8601 形式で記録（Look-ahead バイアス対策）。
  - 入力値変換ユーティリティ _to_float / _to_int を実装（安全な型変換と欠損ハンドリング）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュール（既定ソースに Yahoo Finance の RSS を登録）。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を防止。
  - レスポンス最大バイト数制限 (MAX_RESPONSE_BYTES = 10MB) によるメモリ DoS 対策。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）および記事ID生成方針（正規化後の SHA-256 ハッシュ先頭）。
  - RSS 解析結果を raw_news に冪等保存する設計（ON CONFLICT DO NOTHING を想定）と、銘柄紐付け処理に対応する方針。
  - 大量挿入を想定したチャンクサイズ制御。

- リサーチ（ファクター計算 & 探索） (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio 等を計算（ATR の NULL 伝播制御あり）。
    - calc_value: 最新財務データ（raw_financials）と価格の組合せで PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、DuckDB SQL で集計。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を用いた一括取得）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。サンプル不足時の None 返却。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）。
    - 外部ライブラリへ依存しない純標準ライブラリ実装。

- 戦略 (src/kabusys/strategy/)
  - feature_engineering.py:
    - research 側で計算した生ファクターをマージ・ユニバースフィルタ適用（最低株価・最低平均売買代金）、Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップし features テーブルへ UPSERT（トランザクションによる日付単位置換で冪等性）。
    - ユニバース閾値定義（最低株価 300 円、最低売買代金 5 億円等）。
    - ルックアヘッド防止のため target_date 時点のデータのみ参照。
  - signal_generator.py:
    - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントの変換ユーティリティ（_sigmoid, _avg_scores, 各 compute_* 関数）。
    - weights のマージと再スケール（デフォルト重みを定義、ユーザー重みは検証して合成）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつ十分なサンプル数の場合）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル判定（final_score >= threshold、デフォルト 0.60）。
    - SELL シグナル判定（保有ポジションに対するストップロス -8% / スコア低下など）。SELL は BUY より優先される（買戻し除外）。
    - signals テーブルへの日付単位置換での保存（トランザクション + バルク挿入で原子性）。
    - 欠損コンポーネントは中立値（0.5）で補完して不当な降格を防止。

- パッケージ公開 (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py)
  - 主要 API を __all__ でエクスポート（build_features, generate_signals, calc_momentum 等）。

### セキュリティ & 信頼性 (Security & Reliability)
- API クライアントでのレート制御、リトライ（指数バックオフ）、401 自動リフレッシュを実装し、API 利用時の堅牢性を向上。
- ニュース収集で defusedxml、レスポンスサイズ制限、URL 正規化などを導入して外部入力に対する攻撃面を低減。
- DuckDB への書き込みは ON CONFLICT を利用した冪等操作、トランザクションによる日付単位の置換で原子性を確保。

### 既知の制限 (Known limitations)
- feature_engineering / signal_generator は発注層（execution）には依存しない設計。実際の注文実行ロジック（kabuステーション連携等）は別レイヤで実装予定（execution パッケージは空の初期化のみ）。
- signal_generator の一部条件（例: トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で、現バージョンでは未実装としてコメントで明記。
- news_collector の完全実装（RSS フィードの取得フローや DB マッピング）は設計方針を含むが、現状での細かなエッジケース処理やホワイトリスト方式の URL 検査などは更なる検討が必要。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

---

開発者向けの補足:
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar, raw_news 等）は実運用前に整備・マイグレーションを行ってください。
- 環境変数の必須項目を満たしていないと Settings プロパティで ValueError が発生します。README/.env.example を参照して設定してください。
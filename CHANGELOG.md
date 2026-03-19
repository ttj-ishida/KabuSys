Keep a Changelog に準拠した CHANGELOG.md（日本語）

全般な注意:
- 本プロジェクトはセマンティックバージョニングを採用しています。
- 本ファイルはコードベース（src/kabusys 以下）から実装機能を推測して作成しています。

こちらはリリース履歴です。

# CHANGELOG

すべての重要な変更点はここに記載します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

## [Unreleased]
- 今後の変更・未確定の修正をここに記述します。

## [0.1.0] - 2026-03-19
初回リリース。本リリースではデータ取得、特徴量計算、シグナル生成、研究用ユーティリティ、環境設定などのコア機能を実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = 0.1.0。公開 API として data, strategy, execution, monitoring をエクスポート。
- 環境設定 / 起動時自動.env読み込み
  - 環境変数読み込みモジュールを追加（kabusys.config）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、インラインコメント処理（空白前の # をコメントと認識）など堅牢な解析を実装。
  - Settings クラスを提供し、必須変数およびデフォルト値をプロパティ形式で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境種別検証（development, paper_trading, live）とログレベル検証
    - 環境フラグヘルパー: is_live / is_paper / is_dev
- データ取得クライアント（J-Quants）
  - jquants_client モジュールを追加（kabusys.data.jquants_client）。
  - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライロジックを実装（指数バックオフ、最大 3 回、HTTP 408/429 と 5xx を対象）。
  - 401 Unauthorized 受信時はリフレッシュトークンにより id token を自動更新して 1 回リトライ（無限再帰を回避）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE
  - データ整形ユーティリティ: _to_float / _to_int（頑健な変換ロジック）
  - トークンキャッシュ（モジュールレベル）を備え、ページネーション間で共有
  - 取得時刻 (fetched_at) を UTC ISO8601 で記録し、look-ahead bias 対策に配慮
- ニュース収集モジュール
  - news_collector を追加（kabusys.data.news_collector）。
  - RSS 取得 → 前処理 → raw_news への冪等保存を行う処理の基盤を提供。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等を防止
    - HTTP(S) スキーム以外の URL 拒否（SSRF 対策方針あり）
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保
    - トラッキングパラメータ（utm_*, fbclid, gclid など）を除去して正規化
    - bulk insert チャンク化（_INSERT_CHUNK_SIZE）で一括挿入の安全性向上
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定
- 研究用ファクター計算（research）
  - factor_research を追加（kabusys.research.factor_research）:
    - モメンタム: calc_momentum（1M/3M/6M リターン、MA200 乖離率）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、atr_pct、avg_turnover、volume_ratio）
    - バリュー: calc_value（直近財務データから PER/ROE を算出）
    - 各関数は prices_daily / raw_financials のみを参照し、辞書リストで結果を返す設計
  - feature_exploration（kabusys.research.feature_exploration）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算、パラメータ検証あり
    - calc_ic: スピアマンのランク相関（IC）を計算。ties 対応（同順位は平均ランク）、有効サンプルが不足（<3）なら None を返す
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能
    - rank: 同順位の平均ランク付けを行うユーティリティ
  - research パッケージの __all__ に主要関数を公開
- 特徴量エンジニアリング（strategy）
  - build_features を追加（kabusys.strategy.feature_engineering）:
    - research 側の calc_momentum/calc_volatility/calc_value の結果を統合して features テーブルに UPSERT する処理を提供
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円
    - 標準化: 数値ファクターを Z スコア正規化（外れ値は ±3 でクリップ）
    - target_date 単位で一旦削除して挿入する日付単位置換（トランザクションによる原子性）
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用
- シグナル生成（strategy）
  - generate_signals を追加（kabusys.strategy.signal_generator）:
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出して最終スコア final_score を計算
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）およびユーザ重みのバリデーションと再スケール処理
    - シグナル閾値のデフォルトは 0.60（BUY 判定）
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）で BUY を抑制
    - SELL 条件（エグジット）を実装:
      - ストップロス: 現在終値 / avg_price - 1 < -8%
      - スコア低下: final_score が閾値未満
      - トレーリングストップなど未実装のエグジット条件はコメントで明示
    - positions / prices_daily / ai_scores を参照し、signals テーブルへ日付単位で置換（トランザクションによる原子性）
    - SELL が優先されるポリシー（SELL 銘柄は BUY から除外）
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止
- ロギング
  - 各モジュールに logger を導入し、主要イベント（INFO/WARNING/DEBUG）を出力するよう実装

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 注意事項 / マイグレーション
- 環境変数 JQUANTS_REFRESH_TOKEN 等の必須設定がないと一部機能が稼働しません。README や .env.example を参照して設定してください。
- DuckDB スキーマ（raw_prices / raw_financials / market_calendar / prices_daily / features / ai_scores / positions / signals 等）は別途マイグレーションスクリプトまたはスキーマ作成手順が必要です。
- news_collector の記事 ID は URL 正規化に依存するため、外部ソース仕様変更があると重複判定に影響する可能性があります。
- generate_signals の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加フィールドが必要であり、現バージョンでは未実装。

---

（補足）
- 本 CHANGELOG は与えられたコード内容からの推測に基づき記載しています。実際のリリースノートとして使用する場合は、リリース日・変更点の詳細・既知の問題点をプロジェクト責任者の確認のうえで確定してください。
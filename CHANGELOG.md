# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測した実装内容に基づき作成しています。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- 基本パッケージ初期版を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - トップレベルエクスポート: data, strategy, execution, monitoring

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local からの自動読み込みを提供（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パース機能を実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
  - .env.local は .env を上書き（OS 環境変数は保護）。
  - 設定アクセス用 Settings クラスを提供し各種必須設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
  - デフォルト値の扱い（KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL, DB パス等）と値検証（env/log level の許容値チェック）。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - 冪等性と信頼性:
    - リトライロジック（最大3回、指数バックオフ、408/429/5xx を対象）。
    - 401 時は ID トークンを自動リフレッシュして 1 回リトライ（トークンキャッシュをモジュール内で保持）。
    - ページネーション対応（pagination_key を使用）。
  - API から取得したデータを DuckDB に保存するユーティリティ:
    - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
    - save_* 系（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - raw_prices / raw_financials / market_calendar への保存（ON CONFLICT DO UPDATE による冪等性）。
      - PK 欠損レコードのスキップと警告出力。
  - 入出力変換ユーティリティ (_to_float / _to_int) を提供。
  - 取得時に fetched_at を UTC ISO 形式で記録（Look-ahead バイアス追跡に配慮）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集機能を実装（デフォルトに Yahoo Finance のカテゴリ RSS を含む）。
  - 安全性および堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 等に対する防御）。
    - HTTP/HTTPS スキームのみ許可、受信バイト数上限 (MAX_RESPONSE_BYTES = 10MB)。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリパラメータソート）。
    - 記事 ID は正規化 URL の SHA-256 を用いたハッシュ（先頭を切り出す）などで冪等性を確保（コード中で説明あり）。
  - DB 保存はチャンク化してバルク挿入（_INSERT_CHUNK_SIZE）を行い、挿入件数を正確に返す方針。

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE 等を計算（EPS が 0 or NULL の場合は None）。
    - SQL とウィンドウ関数を用いた DuckDB ベースの実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて計算。horizons の妥当性チェック（1..252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データ不足（<3）や分散ゼロは None を返す。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位は平均ランクで処理（丸め誤差対策で round(..., 12) を使用）。
  - 研究モジュールは pandas 等の外部依存を避け、DuckDB と標準ライブラリで完結する設計。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで算出した raw factor を正規化して features テーブルへ保存する処理を実装。
  - 処理フロー:
    1. calc_momentum / calc_volatility / calc_value からファクターを取得
    2. ユニバースフィルタ（株価 >= 300 円, 20日平均売買代金 >= 5 億円）を適用
    3. 数値ファクターを zscore 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    4. features テーブルへ日付単位での置換（DELETE + INSERT をトランザクション内で実行し原子性を保証）
  - 設定可能な正規化対象カラムやクリップ値はコード内定数として管理。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア (final_score) を計算し、BUY / SELL シグナルを生成して signals テーブルに保存する機能を実装。
  - 実装のポイント:
    - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10（weights 引数で上書き可。無効値はスキップ・再スケール処理あり）。
    - BUY 閾値のデフォルトは 0.60（threshold 引数で変更可能）。
    - Stop-loss は終値 / avg_price - 1 < -0.08（-8%）で優先的に SELL。
    - Bear レジーム判定: ai_scores の regime_score 平均が負（かつサンプル数 >= 3）の場合、BUY シグナルを抑制。
    - 欠損コンポーネントは中立値 0.5 で補完し不当な降格を防止。
    - 保有ポジション（positions テーブル）に対して SELL 判定を行う機能を内包。
    - signals テーブルへは日付単位で置換（DELETE + INSERT をトランザクション内で実行）。
  - 実装メモ:
    - 未実装のエグジット条件としてトレーリングストップや時間決済がコメントで記載（positions に peak_price / entry_date が必要）。

- パッケージ公開 API（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - strategy: build_features, generate_signals を公開
  - research: calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank を公開

### 修正 (Changed)
- （初版リリースのため該当なし）

### 修正 (Fixed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- ニュース XML のパースに defusedxml を利用して XML 攻撃に対処。
- news_collector で受信サイズ上限を設定しメモリ DoS を軽減。
- news_collector で外部 URL の正規化・トラッキングパラメータ除去・スキームチェックを行い SSRF 等のリスクを低減。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルの拡張が必要）。
- execution（発注）層・monitoring 層の実装はこのリリースではスケルトン（インポート対象は存在）にとどまる可能性がある。
- DuckDB テーブルスキーマの具体定義はコード中に明記されていないため、DB マイグレーション/スキーマ管理は別途必要。

---

注: この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、変更点・日付・バージョンなどを実際のコミット履歴やリリースポリシーに基づいて調整してください。
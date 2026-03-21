# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本リポジトリは初回リリース（0.1.0）としての変更点を記載しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - パッケージメタ情報を追加（src/kabusys/__init__.py: version = 0.1.0）。
  - 公開モジュールとして data, strategy, execution, monitoring を定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み順序: OS 環境変数 ＞ .env.local（上書き）＞ .env（未設定時にセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - OS の既存環境変数は保護（protected）され、.env による上書きを制御。
  - .env のパーサーは以下をサポート:
    - コメント行、空行、`export KEY=val` 形式
    - シングル/ダブルクォートおよびバックスラッシュエスケープ処理
    - クォートなしのインラインコメント処理（直前が空白/タブの場合）
  - 必須環境変数取得時に未設定なら ValueError を送出する _require() 実装。
  - Settings プロパティとして以下を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live を検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - is_live / is_paper / is_dev ヘルパー

- データ層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足・財務情報・市場カレンダーを取得するクライアントを実装。
  - レート制限遵守: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）。
  - リトライロジック: 指数バックオフ、最大3回、HTTP 408/429/5xx を対象。429 の場合は Retry-After を尊重。
  - 401 応答時は自動でリフレッシュトークンを使って id_token を更新し 1 回リトライ（無限再帰を防止）。
  - ページネーション対応（pagination_key を使用して全件取得）。
  - DuckDB へ保存するユーティリティを実装（冪等性を保証）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE（PK欠損行はスキップ）。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE（PK欠損行はスキップ）。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
  - 入出力変換ユーティリティ: _to_float / _to_int（空値・不正値を None にする挙動、"1.0" のような小数文字列は int に変換可能だが小数部がある場合は None）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に冪等保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を使用して XML ベースの脆弱性を緩和。
    - HTTP/HTTPS スキームのみ許可、SSRF 緩和を意識した実装（URL 正規化と検証を前提）。
    - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
  - URL 正規化:
    - 小文字化、トラッキングパラメータ（utm_ など）削除、フラグメント削除、クエリキーソート。
    - 記事IDは正規化後 URL の SHA-256 の先頭 32 文字を採用して冪等性を確保。
  - バルク INSERT のチャンク処理、トランザクション化により効率的保存を実現。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを定義。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算・探索・評価ユーティリティを実装。
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照しファクターを計算（モメンタム、ATR、PER/ROE 等）。
    - 各関数は date, code をキーとする dict リストを返す。
    - ウィンドウ不足時の取り扱い（必要な行数が揃わない場合は None を返す）を実装。
  - calc_forward_returns: 将来リターン（デフォルト 1,5,21 営業日）の一括取得（1 クエリで LEAD を使用）。
  - calc_ic: スピアマンランク相関（IC）を計算（同順位は平均ランクで処理）。有効レコードが 3 件未満なら None。
  - factor_summary: count/mean/std/min/max/median を算出（None は除外）。
  - rank ユーティリティ: 同順位を平均ランクで処理する実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - 研究環境で計算した生ファクターを正規化・合成して features テーブルへ保存する処理を実装。
  - 処理フロー:
    1. calc_momentum / calc_volatility / calc_value から生ファクターを取得
    2. ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
    3. 数値ファクターを Z スコア正規化し ±3 でクリップ（外れ値抑制）
    4. features テーブルへ日付単位で DELETE → INSERT（トランザクションで原子性確保）
  - 正規化対象カラムや閾値はコード内定数で管理（_NORM_COLS、_ZSCORE_CLIP 等）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア(final_score) を算出し、BUY / SELL シグナルを生成・保存。
  - コンポーネントスコア:
    - momentum/value/volatility/liquidity/news を計算。欠損コンポーネントは中立値 0.5 で補完。
    - シグモイド変換等のユーティリティを提供（_sigmoid, _avg_scores 等）。
  - デフォルトパラメータ:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - BUY 閾値: 0.60
    - ストップロス: -8%（_STOP_LOSS_RATE）
  - 市場レジーム判定:
    - AI の regime_score の平均が負であれば Bear と判定（サンプル数が最低数未満なら Bear とみなさない）。
    - Bear レジーム時は BUY シグナルを抑制。
  - SELL 判定ロジック:
    1. ストップロス（終値 / avg_price - 1 < -8%）
    2. final_score が threshold 未満
    - 補足: トレーリングストップや時間決済は positions テーブルに peak_price / entry_date が必要で、現時点では未実装。
  - signals テーブルへの書き込みは日付単位の置換（DELETE → INSERT）で原子性を確保。SELL 優先のポリシーを採用。

- strategy パッケージの公開 API (src/kabusys/strategy/__init__.py)
  - build_features, generate_signals を top-level に公開。

### 変更 (Changed)

- 該当なし（初回公開のため変更履歴はなし）。

### 修正 (Fixed)

- 該当なし（初回公開のため修正履歴はなし）。

### 非推奨 (Deprecated)

- 該当なし。

### 削除 (Removed)

- 該当なし。

### セキュリティ (Security)

- XML パースに defusedxml を使用して XML 関連の脆弱性を緩和（news_collector）。
- ニュース収集において受信サイズ上限・トラッキングパラメータ除去・スキーム制約など多数の入力検証を実装し、SSRF / DoS 等のリスクを低減。
- J-Quants クライアントはトークンの自動リフレッシュ、リトライロジックを実装し安全な API 呼び出しを目指す。

### 既知の制限・未実装事項 (Known limitations)

- signal_generator のトレーリングストップ / 時間決済ロジックは未実装（positions テーブルに peak_price / entry_date が必要）。
- execution（発注）層はこのリリースでは空（src/kabusys/execution/__init__.py が存在するのみ）。発注 API との接続は別途実装予定。
- monitoring パッケージの実装は今後のリリースで拡充予定。

---

作者: KabuSys チーム  
初回リリース: 0.1.0 (2026-03-21)
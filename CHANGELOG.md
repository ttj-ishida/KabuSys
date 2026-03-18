# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従い、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-18

初回公開リリース。

### 追加 (Added)
- パッケージ初期化
  - package version を 0.1.0 に設定（kabusys.__init__）。
  - 公開 API として data / strategy / execution / monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
  - .env パーサ実装（コメント・export 形式・クォート・エスケープ対応）。
  - .env.local を上書き読み込みする優先順位を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義（必須項目は未設定時に ValueError を送出）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の列挙）と is_live / is_paper / is_dev のヘルパー。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。以下の機能を提供:
    - レート制限制御（120 req/min）を実装する固定間隔スロットリング（_RateLimiter）。
    - リトライ（指数バックオフ、最大3回）および 429/408/5xx に対する再試行。
    - 401 (Unauthorized) 受信時にリフレッシュトークンから自動で id_token を再取得して1回のみリトライ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ冪等保存する save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ _to_float / _to_int。

- 研究・特徴量探索 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括 SQL で計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関 (Information Coefficient) を計算（欠損/非有限値除外、有効レコード数閾値あり）。
    - rank: 同順位は平均ランクを与えるランク変換（丸め誤差対策で round による正規化実施）。
    - factor_summary: ファクター列ごとの基本統計量（count/mean/std/min/max/median）を算出。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（移動平均カウントチェックにより不足時は None）。
    - calc_volatility: 20日 ATR（atr_20、atr_pct）・20日平均売買代金・出来高比率を計算（true_range 算出で NULL 伝播を制御）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - zscore_normalize を含むユーティリティを re-export（kabusys.data.stats 側の関数を利用）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集機能を実装:
    - fetch_rss: RSS の取得とパース（defusedxml 使用、gzip 対応、受信サイズ上限チェック、リダイレクト検査）。
    - fetch_rss は記事の正規化（URL 正規化、tracking params 除去）、タイトル/本文の前処理（URL 除去・空白正規化）、pubDate のパースを行い NewsArticle 型を返す。
    - _normalize_url / _make_article_id により記事 ID を SHA-256 先頭32文字で生成し冪等性を担保。
    - SSRF 対策: リクエスト前にホストのプライベート判定、リダイレクト時のスキーム/ホスト検査（_SSRFBlockRedirectHandler / _is_private_host）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - save_raw_news: INSERT ... RETURNING による挿入（チャンク単位、トランザクションでまとめてコミット）、新規挿入 ID のリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING / INSERT RETURNING で正確な挿入数を返す）。
    - extract_stock_codes: テキスト中の4桁銘柄コード抽出（known_codes によるフィルタリング、重複除去）。

- データベーススキーマ (kabusys.data.schema)
  - DuckDB 用の DDL 定義を追加（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（主キー・型・チェック制約を含む）。

### 変更 (Changed)
- なし（初回リリースのため既存変更は無し）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- XML パースに defusedxml を採用し XML Bom / entity expansion 攻撃を緩和。
- RSS フェッチで SSRF を強く意識した対策を実装:
  - リクエスト前のホスト判定、リダイレクト時のスキーム/ホスト検査、http/https 以外のスキーム拒否。
  - レスポンスサイズの上限チェックと gzip 解凍後サイズ検証（Gzip bomb 対策）。

### パフォーマンス (Performance)
- J-Quants クライアントに固定間隔レートリミッタを導入し API レート上限を遵守。
- feed/news の DB 保存はチャンク化および単一トランザクションで実行しオーバーヘッドを削減。
- ファクター計算 SQL はスキャン範囲をバッファ（カレンダー日数で）により限定し、1 クエリで複数ホライズンやウィンドウ集約を取得して処理を効率化。

### 内部 (Internal)
- ログ出力（logger.debug/info/warning/exception）を各モジュールで充実させ、運用時のトラブルシュートを容易に。
- ユーティリティ関数（URL 正規化、日付パース、型変換、ランク関数など）を整備。

### 既知の制限 / 今後の作業
- raw_executions の DDL はファイル内で途中から切れているため、Execution 層の完全なスキーマは未完成。
- Strategy / Execution / Monitoring パッケージの実装はこのリリースでは簡易化または未実装の箇所がある可能性あり（__all__ に名を挙げているが内部実装は追加途上）。
- 一部のユーティリティ（例: zscore_normalize）は別モジュール（kabusys.data.stats）に依存しているため、そのモジュールのテスト・ドキュメント化が必要。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や意図されたリリースノートがある場合は、そちらに合わせて調整してください。
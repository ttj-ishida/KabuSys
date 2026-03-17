# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
なお、本リポジトリはバージョン 0.1.0 からの公開を想定した初期実装になります。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主要な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを実装（kabusys.__init__）し、サブパッケージ data, strategy, execution, monitoring を公開。
  - パッケージバージョンを 0.1.0 に設定。

- 設定・環境変数管理（kabusys.config）
  - .env および .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export プレフィックスやクォート、インラインコメントを考慮した .env 行パーサを実装。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェックを行う Settings クラスを実装（J-Quants、kabuステーション、Slack、DB パス等）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）やユーティリティプロパティ（is_live / is_paper / is_dev）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得インタフェースを実装（株価日足、財務情報、マーケットカレンダー）。
  - レート制御: 固定間隔スロットリングに基づく RateLimiter を実装（120 req/min を遵守）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 応答時のトークン自動リフレッシュを実装（1 回のみリフレッシュして再試行）。
  - ページネーション対応（pagination_key を用いた複数ページ取得）。
  - データ取得時の fetched_at（UTC）記録方針を採用して Look-ahead Bias を抑止。
  - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT 句で重複更新を吸収。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防御。
    - HTTP リダイレクト時および初回 URL でスキーム検証（http/https のみ許可）とプライベートアドレス（SSRF）チェックを実施。
    - リダイレクト先も検査するカスタム HTTPRedirectHandler を実装。
    - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）を設け、超過時はスキップ。
    - gzip 圧縮解凍の検証（解凍後のサイズチェック含む）。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去。
  - 冪等性と一意性:
    - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成し、重複挿入を防止。
    - save_raw_news / save_news_symbols / _save_news_symbols_bulk はトランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数を返す。
  - テキスト前処理（URL 除去・空白正規化）や RSS pubDate の堅牢なパース実装。
  - 銘柄コード抽出ユーティリティ（4桁数字抽出・既知銘柄フィルタリング）を実装。
  - 複数ソースを横断する統合収集ジョブ run_news_collection を実装（ソース単位でのエラーハンドリング、銘柄紐付けのバルク挿入）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores などの Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤー。
  - インデックス群（頻出クエリを想定）を定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル作成 → インデックス作成を行う初期化関数を提供。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計方針と差分更新ロジックを実装（差分更新、backfill、品質チェック連携を想定）。
  - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
  - テーブル存在チェック、最終取得日の取得ユーティリティを実装。
  - 市場カレンダーに基づく営業日調整ヘルパーを実装（_adjust_to_trading_day）。
  - 差分更新用ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - run_prices_etl により差分取得 → 保存のワークフローを開始するための基盤実装（date_from/backfill_days ロジック、J-Quants クライアント呼び出し、保存の呼び出しまで実装。※ファイルは途中までの実装）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS/XML パースに defusedxml を採用し、XML を介した攻撃に対する防御を実装。
- RSS フェッチ時にスキーム検証とプライベートアドレス（SSRF）チェックを導入。
- .env 読み込みに失敗した場合の警告を追加（読み込み失敗時に安全にスキップ）。

---

参考: 本CHANGELOGはソースコードの内容から推測して作成しています。実際のリリースノート作成時は追加のユーザ向け・運用向けドキュメント（互換性の注意点、移行手順、環境変数の必須一覧など）を併せて記載してください。
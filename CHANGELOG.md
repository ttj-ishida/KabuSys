# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-17
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - `kabusys` パッケージの初期版を追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - 公開サブパッケージ: `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードの探索はパッケージ位置から .git または pyproject.toml を基準にプロジェクトルートを特定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等のため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサは `export KEY=val` 形式、クォートされた値のバックスラッシュエスケープ、コメント（#）の処理などに対応。
    - .env 上書き時に OS 環境変数を保護するための protected キーセットを導入。
  - 設定オブジェクト `settings` を提供。必須値は取得時に明示的エラーを発生させる (`_require`)。
  - 設定項目のバリデーション:
    - KABUSYS 環境 (`KABUSYS_ENV`) は `development`, `paper_trading`, `live` のみ許容。
    - `LOG_LEVEL` は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のみ許容。
  - 代表的プロパティ:
    - J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）など。

- J‑Quants API クライアント (`kabusys.data.jquants_client`)
  - ベース機能を実装:
    - ID トークン取得 (`get_id_token`)
    - 日足株価取得 (`fetch_daily_quotes`)
    - 財務諸表取得 (`fetch_financial_statements`)
    - JPX マーケットカレンダー取得 (`fetch_market_calendar`)
  - 実装上の重要な設計:
    - レート制限（120 req/min）に準拠する固定間隔スロットリング（内部 `_RateLimiter`）。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）。429 の場合は `Retry-After` ヘッダを優先。
    - 401 受信時はトークンを自動リフレッシュして1回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を用いた取得ループ）。
    - 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止。
    - DuckDB への保存は冪等性を担保（`ON CONFLICT DO UPDATE`）。
  - 保存関数:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を実装。PK 欠損行のスキップ、保存件数のログ出力を行う。
  - 型変換ヘルパ:
    - `_to_float`, `_to_int`（厳密な int 変換ルール: 小数部がある場合は None を返すなど）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからのニュース収集を実装（DataPlatform.md に基づく設計）。
  - 主な機能:
    - RSS 取得（`fetch_rss`）、記事前処理（URL 除去・空白正規化）、記事ID の生成（正規化 URL の SHA-256 先頭32文字）、`raw_news` への冪等保存（`save_raw_news`）。
    - 記事と銘柄の紐付け保存（`save_news_symbols`, `_save_news_symbols_bulk`）。
    - 銘柄コード抽出（4桁数字パターン + known_codes フィルタ）(`extract_stock_codes`)。
  - セキュリティ・堅牢性対策:
    - XML のパースに `defusedxml` を使用し XML Bomb 等を防止。
    - SSRF 対策: リダイレクト毎にスキーム・ホスト検証を行うカスタムリダイレクトハンドラ (`_SSRFBlockRedirectHandler`) と、事前のホストがプライベートかのチェック（DNS 解決して A/AAAA を検査）。
    - URL スキームは http/https のみ許可。
    - レスポンスの最大読み込みサイズを制限（MAX_RESPONSE_BYTES = 10MB）し、gzip 解凍後も検証（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定しての取得、取得後の最終 URL 検証。
  - DB 保存面:
    - バルク挿入はチャンク（最大 _INSERT_CHUNK_SIZE = 1000）で実行し、1 トランザクションにまとめる。
    - `INSERT ... RETURNING` を使用して実際に挿入された記事ID/件数を正確に返す。
  - テスト容易性:
    - HTTP オープン処理は `_urlopen` を介しており、テストでモック差し替え可能。

- DuckDB スキーマ (`kabusys.data.schema`)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル群を定義・初期化する DDL を追加。
  - 主なテーブル:
    - Raw layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature layer: `features`, `ai_scores`
    - Execution layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対する制約（PK、CHECK、外部キー）を定義。
  - よく使われるクエリに備えたインデックスを追加（コード/日付検索やステータス検索向け）。
  - `init_schema(db_path)` でディレクトリ作成・DDL 実行・接続を返す。`:memory:` に対応。
  - `get_connection(db_path)` で既存 DB に接続（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の骨組みを実装:
    - 差分更新の方針（最終取得日からの差分取得、バックフィル機能 `backfill_days`）。
    - 市場カレンダーの先読み（定数化）。
    - 品質チェックの呼び出し箇所を想定（quality モジュールと連携）。
  - 主要要素:
    - ETL 結果を表す `ETLResult` データクラス（品質問題、エラー一覧、簡易判定プロパティなど）。
    - テーブル存在確認 `_table_exists`、最大日付取得 `_get_max_date` のユーティリティ。
    - 市場日の調整ヘルパ `_adjust_to_trading_day`。
    - 差分判定用 API: `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`。
    - 価格差分 ETL ジョブ `run_prices_etl`（date_from 自動算出、backfill の適用、J‑Quants クライアント経由で取得→保存）。※関数はコアの流れを実装（詳細の続きは今後拡張予定）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- news_collector にて SSRF や XML 脆弱性、圧縮爆弾対策を組み込み（上記参照）。
- .env 読み込み時のファイル読み取り失敗は警告にフォールバックして安全に動作。

### 既知の制限 / 今後の課題 (Known issues / TODO)
- ETL パイプラインは差分取得の主要フローを実装済みだが、品質チェック（quality モジュール）や一部のジョブ（例えば完全な calendar/backfill ワークフロー）の詳細実装は別途拡張予定。
- strategy / execution / monitoring サブパッケージはパッケージ構成上存在するが、本リリースでは具体的な戦略ロジックや実行エンジンの実装は含まれていない（今後追加予定）。
- DuckDB 周りは基本的な DDL と保存ロジックを実装しているが、パフォーマンス調整や大規模データのさらなる最適化は今後の改善対象。

---

署名:
- このリリースはソースコードの状態から推測して作成した CHANGELOG です。追加・修正の履歴は実際のコミット履歴やリリースノートに基づいて適宜更新してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-17

### 追加
- 新規パッケージ「KabuSys」を初版リリース
  - パッケージ構成:
    - kabusys.config: 環境変数/設定管理
    - kabusys.data: データ取得・保存・ETL（jquants_client, news_collector, schema, pipeline 等）
    - kabusys.strategy: 戦略用パッケージ（初期プレースホルダ）
    - kabusys.execution: 発注/実行用パッケージ（初期プレースホルダ）
  - パッケージ版番号: `0.1.0`

- 環境設定（kabusys.config.Settings）
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: `.git` または `pyproject.toml` を親ディレクトリから探索して判定
    - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサ実装（コメント・export プレフィックス・クォート・エスケープ等に対応）
  - 環境変数の必須チェック `_require()` を提供（未設定時は ValueError）
  - 代表的な設定プロパティを提供:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション API: KABU_API_PASSWORD / KABU_API_BASE_URL（デフォルトあり）
    - Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH / SQLITE_PATH（デフォルトパス・Path 型で取得）
    - 実行環境判定: KABUSYS_ENV（development / paper_trading / live の検証）
    - ログレベル検証: LOG_LEVEL（DEBUG/INFO/... の検証）  
  - 設定は型注釈・プロパティで提供され、実運用での安全性を高める設計

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ `_request` を実装
    - レスポンス JSON のデコードとエラーハンドリング
    - ページネーション対応（pagination_key を使用）
    - 再試行ロジック（指数バックオフ, 最大3回）
    - HTTP 408/429/5xx を対象にリトライ。429 の場合は `Retry-After` を優先
    - ネットワークエラー（URLError / OSError）へのリトライ
  - 認証とトークン管理
    - リフレッシュトークンから id_token を取得する `get_id_token`
    - モジュールレベルの id_token キャッシュ（ページネーション間共有）
    - 401 受信時に自動で一度トークンをリフレッシュして再試行（無限再帰対策あり）
  - レート制御
    - 固定間隔スロットリング（120 req/min を満たす _RateLimiter 実装）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes（株価日足：OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 各関数は INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新
    - フェッチ時刻を UTC 文字列で記録（fetched_at）し、look-ahead bias を追跡可能に
  - データ変換ユーティリティ `_to_float`, `_to_int`（不正値に対する堅牢な変換）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ保存するフロー実装
    - fetch_rss: RSS 取得・XML パース・記事整形（title, content, pubDate 解析）
    - preprocess_text: URL 除去・空白正規化
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保つ
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート
    - _make_article_id/_normalize_url 実装
  - セキュリティ対策・堅牢化
    - defusedxml を用いた XML パース（XML Bomb 等への対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - レスポンス中のリダイレクト先を事前検査するカスタム RedirectHandler（プライベートアドレス拒否）
      - ホストのプライベートIP判定（直接 IP と DNS 解決の両方を検査）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信・gzip 解凍後も検査（Gzip bomb 対策）
    - User-Agent / Accept-Encoding の設定
  - DB 保存機能（DuckDB）
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、実際に挿入された記事IDリストを返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複をスキップ）。RETURNING を利用して挿入件数を正確に把握。
  - 銘柄抽出ユーティリティ
    - extract_stock_codes: テキスト中の4桁数字候補から既知銘柄セットに含まれるものだけを抽出（重複排除）
  - 統合ジョブ run_news_collection を提供
    - 複数ソースの独立実行、個別エラーは他ソースに影響しない設計
    - 新規挿入記事のみを対象に銘柄紐付けを一括登録

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定
  - 頻出クエリ向けインデックス定義を追加
  - init_schema(db_path) 実装: 親ディレクトリ自動作成、すべての DDL とインデックスを実行して接続を返す（冪等）
  - get_connection(db_path) 実装: 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass: ETL 実行結果の構造（取得数・保存数・品質問題・エラーメッセージ等）を定義
    - quality_issues を整形して辞書出力する to_dict を提供
  - 差分更新ヘルパー:
    - _table_exists / _get_max_date: テーブル存在確認と最大日付取得
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日に調整（最大30日遡り）
  - run_prices_etl 実装（差分取得 + 保存）
    - 差分ロジック: DB の最終取得日から backfill_days（デフォルト 3 日）分さかのぼって再取得して API 後出し修正を吸収
    - デフォルト最小取得開始日: 2017-01-01
    - J-Quants クライアントの fetch/save を利用して取得・保存を行う
  - その他設計方針:
    - 品質チェックモジュールとの連携（quality モジュールは別途実装想定）
    - id_token を引数注入可能にしてテスト容易性を確保

### セキュリティ / 堅牢化
- 外部通信に関する各種セーフガードを実装
  - RSS / HTTP: スキーム検証、プライベートIP拒否、受信サイズ上限、gzip 解凍後の再チェック
  - XML パースに defusedxml を使用
  - API クライアント: リトライ時のバックオフ、Retry-After の尊重、401 の安全な自動リフレッシュ制御
- .env 読み込み時に OS 環境変数を保護する protected 機能を提供（.env.local による上書きルールを含む）

### 内部実装・質の向上
- 型ヒント（typing）と docstring を広範に採用し、可読性と保守性を向上
- ログ出力を適所に追加（info/warning/exception）して運用時の観察性を向上
- DuckDB に対するトランザクション管理（begin/commit/rollback）を実装して一貫性を確保
- CSV/SQL インジェクション等を意識してパラメタライズあるいはプレースホルダでのバルク挿入を実施（ただし一部ダイナミックな SQL 文字列組み立ては残るため運用時に注意）

### 既知の制約 / 注意点
- pipeline.run_prices_etl を含む一部 ETL 関数は本コード断片の終端で途切れている（続き実装が必要）
- news_collector の DNS 解決失敗時の扱いは「安全側（非プライベート）として通過」となっているため、特定環境では意図しないホスト解決挙動に注意が必要
- DuckDB の型／制約は実運用でのデータ例に対して更なる調整が必要になる可能性あり

---

今後の予定（推測）
- pipeline の完全実装（価格・財務・カレンダーの全 ETL ジョブ、品質チェックの統合）
- strategy / execution の具体実装（シグナル生成、注文送信、ポジション管理）
- モニタリング（Slack 通知等）の実装および運用のドキュメント化

この CHANGELOG はコードベースから推測して作成したため、実際のコミット履歴やプロジェクト管理上のリリースノートと差異がある場合があります。必要であれば実際のコミットやリリース計画に合わせて調整します。
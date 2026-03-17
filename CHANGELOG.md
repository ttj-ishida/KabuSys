# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

現在のバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下の主要機能・設計方針を含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys/__init__.py にて version と公開モジュールを定義（data, strategy, execution, monitoring）。
  - strategy/、execution/、monitoring/ パッケージの雛形を追加（将来の実装箇所として用意）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を順に読み込み。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート（テスト用途など）。
  - .env パーサは以下をサポート:
    - `export KEY=val` 形式
    - シングル/ダブルクォートとバックスラッシュエスケープの扱い
    - インラインコメントの扱い（クォート有り/無しでの挙動を区別）
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack トークン等の必須設定を明示的に要求（未設定で ValueError）。
    - デフォルト値: KABUSYS_ENV=development、KABUSYS_API_BASE_URL、データベースパス等。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev の便利プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期BS/PL）、JPXマーケットカレンダー取得を実装。
  - 設計上の特徴:
    - API レート制限を遵守する固定間隔スロットリング（120 req/min の _RateLimiter）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回のみリトライ（無限再帰を防止）。
    - ページネーション対応（pagination_key を用いて全ページ取得）。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション間で使い回し。
    - データベース保存関数は冪等性を保証（DuckDB への INSERT ... ON CONFLICT DO UPDATE を利用）。
    - 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止。
  - ユーティリティ: 型変換関数 `_to_float` / `_to_int` を用意（不正値や小数切り捨てを回避）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する処理を実装。
  - 設計上の特徴・安全対策:
    - 記事 ID は URL を正規化してから SHA-256 の先頭32文字を採用（冪等性）。
    - URL 正規化で utm_* 等のトラッキングパラメータ除去、スキーム/ホストの小文字化、クエリソート、フラグメント削除を実施。
    - SSRF 対策:
      - リダイレクト前後でスキーム検証（http/https のみ）およびホスト/IP のプライベート判定を実施（_SSRFBlockRedirectHandler, _is_private_host）。
      - DNS 解決して A/AAAA を検査。解決失敗は安全側で通過。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - URL 抽出とテキスト前処理（URL 除去・空白正規化）。
    - 記事の DB 保存はバルクチャンク（デフォルト1000件）で INSERT ... ON CONFLICT DO NOTHING RETURNING を使用し、新規挿入 ID のみを返す。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、与えられた known_codes セットに含まれるものだけを採用。重複排除済み。
    - run_news_collection により複数ソースを独立して収集し、失敗に強い実行（1 ソース失敗しても他は継続）。

- DuckDB スキーマと初期化（kabusys.data.schema）
  - DataSchema に基づくスキーマを定義・初期化する init_schema(db_path) を実装。
  - 3 層（Raw / Processed / Feature）＋ Execution 層の主要テーブルを定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK）、型、NOT NULL を厳密に定義。
  - よく使われるクエリ向けに複数のインデックスを定義（code/date や status 等）。
  - get_connection(db_path) を提供（既存 DB へ接続。init_schema は初回のみ呼ぶ設計）。
  - DB ファイルの親ディレクトリが存在しない場合は自動作成。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新重視の ETL 設計を実装（差分更新、backfill、品質チェック連携などの方針をコード化）。
  - ETLResult dataclass を導入し、ETL のメタ情報（取得数・保存数・品質問題・エラー等）を表現・辞書変換可能にした。
  - 市場カレンダーへの先読み（lookahead）や最小データ日付設定を含む定数を追加。
  - テーブル存在チェック・最終取得日の取得ユーティリティを実装（_table_exists, _get_max_date, get_last_price_date 等）。
  - 非営業日の調整ヘルパーを実装（_adjust_to_trading_day）。
  - run_prices_etl 等の個別 ETL ジョブ（差分の自動計算、backfill-days の扱い、jquants_client を用いた取得と保存）を実装。

### 変更 (Changed)
- （初版のため履歴なし）

### 修正 (Fixed)
- （初版のため履歴なし）

### セキュリティ (Security)
- ニュース収集の SSRF 緩和策、defusedxml の採用、レスポンスサイズ制限、リダイレクト先の検証など、外部データ取得に伴うリスクを考慮した実装を追加。
- HTTP リダイレクト時にプライベートアドレスや不正スキームを拒否する処理を導入。

### 非推奨 (Deprecated)
- （なし）

### 削除 (Removed)
- （なし）

### 既知の制限 / 今後の課題
- strategy／execution／monitoring パッケージは雛形のみで、戦略ロジックや発注実装・監視機能は未実装。
- ETL の品質チェックモジュール（kabusys.data.quality）は参照されているが、詳細実装やルール整備は今後の作業対象。
- 現在のテストカバレッジは不明（テスト用フックは一部実装済み：_urlopen の差し替え等）。ユニットテスト・統合テストの整備を推奨。

---

参考:
- バージョンは kabusys/__init__.py の __version__ に合わせています: 0.1.0
- 日付は本リリース作成日を設定しています。
# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
日付はこのコードスナップショット作成日（2026-03-18）を使用しています。

全般的な注記
- このリポジトリは日本株の自動売買/データ基盤をターゲットとしたパッケージ「KabuSys」です。  
- 現在のパッケージバージョンは 0.1.0（初回リリース相当）です。  
- 一部モジュール（strategy, execution, monitoring）はプレースホルダとして存在します。

[0.1.0] - 2026-03-18
---------------------------------------
Added
- パッケージの基本情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - パッケージ公開対象モジュールとして data, strategy, execution, monitoring を __all__ に定義。

- 環境設定/ローディング機能（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードする仕組みを実装。
  - .env のパース機能を強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、行末のコメント処理を考慮。
    - 無効行・コメント行のスキップ。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション。
    - はじめての環境変数未設定時は明確な例外メッセージを投げる _require を実装。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）を Path として取得・展開。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - 設計上の特徴:
    - API レート制御（120 req/min）の固定間隔スロットリングを実装（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 の場合はリフレッシュトークンで自動リフレッシュして 1 回再試行。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制する方針。
  - DuckDB への保存関数（save_daily_quotes／save_financial_statements／save_market_calendar）を実装：
    - ON CONFLICT DO UPDATE による冪等性を確保。
    - PK 欠損行のスキップとログ出力。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、安全な変換を行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する統合モジュールを実装。
  - 設計上の特徴（安全性・品質重視）:
    - defusedxml を利用して XML Bomb 等の攻撃を防御。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）により一意の記事 ID（SHA-256 の先頭32文字）を生成し冪等性を担保。
    - SSRF 対策:
      - リダイレクト時にスキーム検査・ホストがプライベートアドレスかどうかをチェックする専用 RedirectHandler を導入。
      - リクエスト前にホストの事前検証を実施。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および Content-Length/Gzip 解凍後のサイズ検査でメモリ DoS/Gzip bomb を防止。
    - HTTP/HTTPS スキームのみ許可、mailto/javascript/file スキームの排除。
    - RSS の pubDate をパースして UTC naive datetime に変換。パース失敗時は warning ログと現在時刻で代替。
    - DB 保存はバルク INSERT（チャンク処理）・トランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された ID を返す（ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出ロジック（4桁数字パターン）を実装し、既知銘柄セットでフィルタする関数提供。
    - run_news_collection で複数ソースを順次処理、ソース単位で個別にエラーハンドリング。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を網羅的に定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - カラム制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設計に反映。
  - よく使われるクエリ向けのインデックス（code×date, status, signal_id など）を定義。
  - init_schema(db_path) で親ディレクトリ作成、DDL 実行して接続を返すユーティリティを実装。
  - get_connection(db_path) で既存 DB への接続を取得。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（差分取得＋バックフィル）を行う ETL ヘルパー群を実装。
  - 機能:
    - DB から最後の取得日を問い合わせるユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日調整ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl: 差分算出（最終取得日 - backfill_days を考慮）→ J-Quants から取得 → 保存（jquants_client.save_*）のフローを実装（差分取得の方針、デフォルトバックフィル日数 3 を採用）。
    - ETLResult データクラスを導入し、処理結果、品質問題、エラー等を集約。has_errors / has_quality_errors / to_dict を提供。
  - 設計方針:
    - 差分更新（最小単位は営業日1日）とバックフィルで API の後出し修正に対応。
    - 品質チェックはエラー重大度に応じて ETL の継続可否を呼び出し元に委ねる（Fail-Fast ではない）。

Changed
- 初期リリースのため、"Added" に該当する実装が多く、既存からの変更はなし。

Fixed
- 初回リリースのため該当なし。

Security
- ニュース収集の SSRF 対策、XML パースの安全化、レスポンスサイズ制限、URL スキーム検査など、外部入力に起因する攻撃を多数考慮した実装を追加。
- 環境変数の自動ロードはプロジェクトルートを基準にしており、テストで無効化できるフラグを提供。

Known issues / Notes
- run_prices_etl のソースでは末尾の return 文が不完全（スナップショットの終端が途中で切れているように見える箇所があります）。意図としては (fetched_count, saved_count) を返す設計ですが、実際のコード状態では構文/実装の補完が必要です（本CHANGELOGはコードからの推測に基づくため、実装途中の可能性があります）。
- strategy, execution, monitoring パッケージは初期プレースホルダで、中身の実装は未完成または別コミットで追加予定。
- jquants_client._ID_TOKEN_CACHE はモジュールレベルで単純キャッシュしており、長寿命プロセスでのトークン管理は運用に応じた検討が必要。
- extract_stock_codes は単純に 4 桁数字を拾う実装のため、文脈上の誤検出（例えば記事中の一般的な4桁数字）を除去するためには追加の NLP/辞書ベースの正規化が有効。

Migration / Usage notes
- 初回起動前に DuckDB スキーマを初期化するには:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参照して .env を作成
- 自動で .env を読み込ませたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- news_collector の外部 HTTP 呼び出しは _urlopen をモックしてテスト可能。

開発者向け
- ロギングが各モジュールに埋め込まれているため、デバッグ時は LOG_LEVEL を環境変数で調整。
- news_collector の SSRF 判定は DNS 解決できない場合は「非プライベート」とみなす安全側判断（実運用環境の DNS 構成によって動作が変わる点に注意）。

リンク / 参考
- この CHANGELOG はコードベースのスナップショットから推測して作成しています。実装の詳細・補完は該当ソースを参照してください。

--- 
（END）
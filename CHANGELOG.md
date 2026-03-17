# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※ 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています（自動生成ではなくコードリーディングに基づく要約）。実際のコミット履歴とは差異があります。

## [Unreleased]

追加予定 / 既知の問題・TODO
- run_prices_etl の戻り値がファイル末尾で不完全（タプルの最後が欠けている）ため修正が必要。現在の状態だと構文エラーや想定しない動作になる可能性あり。
- strategy / execution / monitoring パッケージは __init__.py のみで実装が空。実際の自動売買ロジック・発注実装・監視機能の追加が必要。
- 単体テスト・統合テストの追加（特にネットワーク依存部および DB 操作部をモックするテスト）。
- env 自動ロードの挙動を明示的にドキュメント化（テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を使うこと等）。
- J-Quants クライアントに対するメトリクス収集やより詳細な監視（リトライ頻度、レート制限待機時間など）の導入検討。

---

## [0.1.0] - 2026-03-17

初期公開リリース。以下の主要機能を実装・提供。

### Added
- パッケージメタ情報
  - kabusys.__version__ を "0.1.0" に設定。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索する方式で実装（CWD に依存しない）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理を考慮）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得メソッドを定義（必須 env 未設定時は ValueError を送出）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API ベース実装（トークン取得、株価日足・財務データ・マーケットカレンダーの取得）。
  - レート制限を守る固定間隔スロットリング実装（120 req/min に対応する RateLimiter）。
  - 冪等保存: DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE により重複を排除。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、HTTP 408/429 および 5xx を対象）。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュ処理（1 回限定のリフレッシュと再試行）。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - データ取り込み時に fetched_at を UTC で記録し、Look-ahead bias を抑制。
  - 値変換ユーティリティ (_to_float / _to_int) を実装（空値や不正フォーマット対策、"1.0" のような float 文字列の適切処理など）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得・正規化して DuckDB に保存するワークフローを実装。
  - defusedxml を使用した安全な XML パースにより XML Bomb やその他の攻撃リスクを低減。
  - URL 正規化処理（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - 記事IDを正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - SSRF 対策:
    - fetch 前にホストのプライベートアドレス検査を実施。
    - リダイレクト時にスキームとリダイレクト先のホストを検査するカスタム HTTPRedirectHandler (_SSRFBlockRedirectHandler) を導入。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み上限を超える場合はスキップ。
    - gzip 圧縮対応と解凍後サイズチェック（Gzip bomb 対策）。
  - テキスト前処理（URL 削除、空白正規化）。
  - DuckDB への保存は対話的にトランザクションでまとめて実行し、INSERT ... RETURNING を用いて実際に挿入された記事 ID のリストを返す（save_raw_news）。
  - 記事と銘柄の紐付けを行う関数（save_news_symbols / _save_news_symbols_bulk）を提供。チャンク処理による効率化と ON CONFLICT で重複をスキップ。
  - 銘柄コード抽出ロジック（4桁数字パターン）を実装し、known_codes に基づくフィルタリングを行う（extract_stock_codes）。
  - run_news_collection により複数 RSS ソースを横断して収集→保存→銘柄紐付けまでの統合ジョブを提供。各ソースは独立してエラーハンドリングされ、1 ソース失敗でも他ソースは継続。

- スキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 各種テーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - パフォーマンス向けにインデックスを定義（頻出クエリパターンを想定）。
  - init_schema(db_path) を提供し、ディレクトリ自動作成やテーブル作成を冪等に実行。
  - get_connection(db_path) で既存 DB への接続を取得可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 実行結果を表す dataclass (ETLResult) を実装。品質チェック結果やエラーの集約、辞書化サポートを提供。
  - 差分更新のためのユーティリティ（_table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分取得／バックフィルロジック、_MIN_DATA_DATE、バックフィル日数の扱い、jquants_client.fetch & save 呼び出し）。※ ただしファイル末尾で戻り値が不完全になっているため要修正（Unreleased に記載）。

### Security
- ニュース収集での SSRF 対策と受信サイズ制限、defusedxml の採用により外部フィード取り込み時の安全性を強化。
- .env パーシングではクォート・エスケープを考慮し、誤った評価のリスクを低減。

### Performance
- J-Quants API 呼び出しに対するレートリミッタ実装（120 req/min 固定間隔スロットリング）。
- DB 保存時にバルク INSERT（チャンク処理）や ON CONFLICT を活用し IO/競合コストを低減。
- news_collector と news_symbols のチャンク INSERT による効率化。

### Fixed
- （初期リリースのため該当なし。以降のリリースでバグ修正を記載予定）

---

参考:
- 主要ファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py

もし詳しいリリース日付や個々のコミットメッセージが必要であれば、実際の git ログを提供してください。今回の CHANGELOG はコード内容から推測した「初期リリースの機能一覧と既知の問題」に基づいています。
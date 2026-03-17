# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-17

最初の公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。主な追加と設計上のポイントは以下の通りです。

### Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定し、主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動的に読み込む機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため、CWD に依存しないロードが可能。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env の行パーサは `export KEY=val`、クォートやエスケープ、行内コメント処理に対応。
  - OS 環境変数を保護する `protected` オプションを使用した上書き挙動をサポート。
  - `Settings` クラスでアプリケーション設定をプロパティとして公開（J-Quants トークン、kabu API、Slack、DB パス、環境/ログレベル判定など）。無効値・未設定時の検証とエラーを実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しの HTTP ラッパーを実装（JSON デコード、エラーハンドリング）。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を遵守する `_RateLimiter`。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンからのトークン再取得を 1 回実施してリトライ（無限再帰対策あり）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存機能（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装（空値や不正値を安全に None に変換、"1.0" 型の処理など）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 防止を考慮。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事収集と DuckDB への保存を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb や類似攻撃対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないかの検査、リダイレクト時の事前検証ハンドラ。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存はトランザクションでまとめ、INSERT ... RETURNING を使って実際に挿入された ID を正確に取得:
    - save_raw_news（raw_news）
    - save_news_symbols / _save_news_symbols_bulk（news_symbols）
  - 銘柄コード抽出ロジック（4桁数字候補から known_codes に基づくフィルタリング）と、集約ジョブ run_news_collection を実装。
  - HTTP オープン処理はテスト容易性のため _urlopen をモック可能に設計。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けのインデックスを定義。
  - `init_schema(db_path)` で DB ファイルの親ディレクトリ自動作成および DDL 実行、`get_connection` で既存接続取得。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新のためのヘルパー関数実装（テーブル存在チェック、最終日取得）。
  - 市場カレンダーによる営業日調整 `_adjust_to_trading_day`。
  - ETL 実行結果を表す `ETLResult` データクラス（品質問題・エラーの集約、辞書化機能）。
  - run_prices_etl を含む個別 ETL ジョブ群の骨組み（差分取得・backfill_days による後出し修正吸収方針、J-Quants による取得と保存の連携）。
  - データ品質チェック（quality モジュールとの連携を想定する設計）を想定したフローを実装。

### Security
- news_collector に SSRF 対策、defusedxml 使用、受信サイズ制限、リダイレクト時スキーム/ホスト検証を導入。
- .env 読み込み時に OS 環境変数を保護する仕組みを実装（.env.local による上書きは可能だが protected により OS の値を保持）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュし、ページネーション間で共有する設計。get_id_token の呼び出しからの無限再帰を防ぐため allow_refresh フラグを使用。
- DuckDB への保存は可能な限り冪等性（ON CONFLICT）を担保しており、raw_news 周りは INSERT ... RETURNING を活用して実挿入数を帰す。
- news_collector の URL 正規化はトラッキングパラメータを取り除き、クエリをソートして一意化を図る設計。
- ETL パイプラインの一部関数は外部 quality モジュールに依存する設計（品質問題の検出と報告を分離）。

### Known issues / Limitations
- pipeline モジュール内の run_prices_etl の末尾処理がファイルスニペットの切り出しにより不完全に見える箇所があります（このリリースの実装では差分取得→保存→ログ出力までの流れは実装されていますが、追加の後処理や品質チェックの統合は継続的に整備予定）。
- 本リリースはコアデータ基盤（取得・保存・スキーマ・ETL 基盤・ニュース収集）を中心に実装しており、strategy / execution / monitoring の具体的な戦略や発注ロジックは別途実装が必要です。
- 外部サービス依存（J-Quants, RSS ソース, kabu API, Slack など）については環境変数での設定とテスト用のモック注入を想定しています。

---

作業ログの要約:
- 初回リリースとしてデータ取得・保存基盤とニュース収集、安全対策、設定管理、DuckDB スキーマ、ETL の骨組みを実装しました。次のマイルストーンでは戦略実装、実行エンジン、監視アラート、品質チェックの拡充を予定しています。
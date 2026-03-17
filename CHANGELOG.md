CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは「Keep a Changelog」方式に従っています。  

フォーマット:
- Unreleased: 今後の変更（開発中）
- 各リリースは日付付きで記載し、Added / Changed / Fixed / Security 等のセクションで整理します。

Unreleased
----------

- なし（初回リリースに相当する 0.1.0 を含む）

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - src/kabusys/__init__.py
    - パッケージバージョン __version__ = "0.1.0" を設定。
    - 公開サブパッケージ: data, strategy, execution, monitoring を定義。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定値を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - .env のパース機能: コメント、export プレフィックス、シングル／ダブルクォート、エスケープ処理、インラインコメント対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite） / 環境（development/paper_trading/live） / ログレベル検証 等。
  - 必須環境変数未設定時は ValueError を送出する _require ヘルパー。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - データ取得: 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得機能を実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライ機構: 指数バックオフによるリトライ（最大 3 回）。対象ステータスに対する再試行（408, 429, 5xx）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけ再試行（無限再帰防止）。
  - ページネーション対応（pagination_key）で全ページを逐次取得。
  - モジュールレベルで id_token をキャッシュ（ページ間で共有）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等性確保のため INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC (Z) で記録して「いつデータを知り得たか」を追跡可能に。
    - PK 欠損行のスキップとログ出力。
  - 型変換ユーティリティ (_to_float, _to_int) を追加。境界ケース（空文字列、float 文字列等）に対する挙動を明確化。

- RSS ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィード取得、テキスト前処理、記事保存、銘柄紐付けまでの一連処理を実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パースで XML Bomb 等に対策。
    - SSRF 対策: リダイレクトハンドラでリダイレクト先のスキーム（http/https）とプライベートアドレス判定を事前検査。
    - URL スキーム検証（http/https のみ許可）。ローカル/ファイルスキーム等を排除。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再検査でメモリ DoS/Gzip bomb に対処。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。正規化後の SHA-256（先頭32文字）で記事IDを生成、冪等性を確保。
  - RSS 内の pubDate を UTC に正規化して格納（パース失敗時は警告ログと現在時刻代替）。
  - DB 保存:
    - save_raw_news でチャンク INSERT + RETURNING を利用し、実際に挿入された記事 ID を返す実装（トランザクションでまとめてコミット / ロールバック）。
    - save_news_symbols / _save_news_symbols_bulk で (news_id, code) 紐付けをチャンクで冪等保存（ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出ユーティリティ (extract_stock_codes): 4桁数字候補を抽出し、known_codesセットでフィルタリング、順序と重複除去を保持。
  - run_news_collection で複数ソースの独立処理、エラーハンドリング（1ソース失敗でも他は継続）、新規保存数の集計、既知銘柄との紐付けを実装。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（+ Raw/Execution の補助テーブル）を含む完全なスキーマを定義。
  - 各テーブルに対して NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY 制約を付与。
  - 主要クエリ用のインデックス定義を追加（例: prices_daily(code, date)、signal_queue(status) 等）。
  - init_schema(db_path) により親ディレクトリ自動作成 → DuckDB 接続 → DDL/インデックス実行（冪等）。
  - get_connection(db_path) で既存 DB への接続取得（スキーマ初期化は行わない）。

- ETL パイプラインの基礎を追加（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を追加し、ETL の集計結果（取得数、保存数、品質問題、エラー等）を格納・辞書化可能に実装。
  - 差分更新のためのヘルパー: テーブル存在チェック、最大日付取得（_get_max_date）、市場カレンダーに基づく営業日調整(_adjust_to_trading_day)。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパーを追加。
  - run_prices_etl 実装（差分更新ロジック、backfill_days デフォルト 3 日、最小データ日付 2017-01-01、fetch → save の流れ）を追加。
  - 市場カレンダー先読みや品質チェック（quality モジュールとの連携）を想定した定数と設計方針を反映。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS/NW 周りで複数のセキュリティ対策を導入:
  - defusedxml の採用、SSRF チェック（リダイレクト時のホスト/IP 検査）、URL スキーム制限、受信バイト制限、gzip 解凍後のサイズ検査。
- 環境変数読み込みで OS 環境変数の上書きを防止する protected 機能を実装（.env ロード時の安全策）。

Notes / Implementation details
- 多くの DB 操作は DuckDB のプレースホルダを用いた executemany / 並列チャンク処理を行い、挿入の冪等性と性能を意識した実装になっています。
- jquants_client のリトライ/バックオフは API レート制限・サーバ側の Retry-After ヘッダを尊重する設計です。
- pipeline 側は品質チェック（quality モジュール）との連携を前提にしており、品質チェックの結果は ETLResult に含めて外部で処理を委ねる設計です。
- 設定・環境変数の検証が導入されており、不正な KABUSYS_ENV / LOG_LEVEL の値は早期に検出されます。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（現状はパッケージプレースホルダ）。
- pipeline のさらなる完成（品質チェック呼び出し、calendar の先読み反映、並列処理最適化）。
- テストカバレッジの拡充（外部 API のモック、ネットワーク例外・XML 攻撃ケース等）。

--- 

参照: 各モジュールの docstring / コメントに記載された設計原則および DataPlatform/DataSchema の記載に準拠して実装されています。
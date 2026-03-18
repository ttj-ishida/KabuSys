# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはリポジトリ内のソースコード（2026-03-18 時点）から機能・設計・既知の問題を推測して作成した初回リリース向けの変更履歴です。

履歴のバージョンや日付はコード内の __version__（0.1.0）および現時点の日付を用いています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初期リリース: kabusys パッケージ（バージョン 0.1.0）
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理（Settings クラス）
    - kabusys.data: データ取得・保存関連（jquants_client, news_collector, schema, pipeline 等）
    - kabusys.strategy: 戦略モジュールのプレースホルダ
    - kabusys.execution: 発注/実行関連のプレースホルダ
  - パッケージ公開情報: src/kabusys/__init__.py に __version__= "0.1.0"、__all__ の定義あり

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応
  - Settings クラスを公開（J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル判定 などのプロパティ）
  - 入力検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須 env 未設定時のエラー発生

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 設計・実装の特徴:
    - レート制限対応: 固定間隔スロットリングで 120 req/min を尊重（内部 RateLimiter）
    - リトライロジック: 指数バックオフ（最大試行回数 3）、HTTP 408/429/5xx やネットワークエラーをリトライ
    - 401 発生時の自動トークンリフレッシュ（最大 1 回、ループ防止あり）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - ページネーション対応（pagination_key）
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）
    - データ取得時に fetched_at を UTC（ISO8601）で保存して Look-ahead バイアスの追跡を可能に
    - 型注釈とユーティリティ関数 (_to_float/_to_int) による堅牢化

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DuckDB への保存ワークフローの実装
  - 主な機能・設計:
    - デフォルト RSS ソース（例: Yahoo Finance カテゴリ）
    - RSS の XML 解析に defusedxml を使用し XML ボム等対策
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査（Gzip-bomb 対策）
    - リダイレクト時の SSRF 対策: リダイレクト先のスキーム確認とプライベートIP/ループバックの検査（専用 RedirectHandler）
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリ整列
    - 記事ID: 正規化 URL の SHA-256 先頭32文字（冪等性確保）
    - テキスト前処理: URL 除去・空白正規化
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク単位で実行し、INSERT RETURNING で実際に挿入された ID リストを返す。1 トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT RETURNING による挿入数取得）
    - 銘柄コード抽出: 正規表現で 4 桁の候補を抽出し、known_codes によるフィルタリング（重複除去）

- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）に対応するテーブル群を定義
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種チェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を定義
  - 頻出クエリ向けインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成後に DDL を一括実行し、接続を返す
  - get_connection(db_path) により既存 DB へ接続可能

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新型 ETL 実装（差分開始日算出、backfill、品質チェックフック想定）
  - ETLResult dataclass により ETL 結果（取得数/保存数/品質問題/エラー）を構造化し to_dict() でシリアライズ可能
  - デフォルト値:
    - J-Quants のデータ開始日: 2017-01-01
    - カレンダー先読み: 90 日
    - デフォルト backfill_days: 3 日
  - run_prices_etl の骨組み実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes）

Security
- ニュース収集周りの SSRF 防止・XML 脆弱性対策（defusedxml・リダイレクト検査・プライベートIP判定）
- 外部接続周りでのスキーム検証（http/https のみ許可）
- .env 読み込みにおける保護機構（OS 環境変数を protected として上書き制御）

Changed
- （初版のため「変更」はなし）

Fixed
- （初版のため「修正」はなし）

Known issues / Notes / TODO
- run_prices_etl の実装に未完成の戻り値:
  - ファイル末尾の run_prices_etl 実装では return len(records), としており、本来返すべき (fetched_count, saved_count) のタプルで saved_count が返されていない（おそらく保存結果の saved 変数を返す意図）。このため現在の実装は構文的にはタプルを返すものの saved 値が欠如しており、呼び出し側で期待する戻り値と不整合になる可能性がある。要修正。
- パッケージ内に strategy/ と execution/ の __init__.py が空でプレースホルダ状態。戦略・実行ロジックは未実装。
- 単体テストや統合テストの実装は見られない（_urlopen 等がテストフック用に設計されているがテスト未提供）。
- ロギングの初期設定（ハンドラ、フォーマット）やエラーレポーティングの統一的な方針は未実装。サービス環境でのログ設定が必要。
- エラーハンドリングの観点で専用の例外クラスは存在せず、ランタイム例外を用いる箇所があるため、API 利用時は呼び出し元での堅牢な例外処理が必要。
- news_collector の DNS 解決で例外が起きた場合に「安全側として通過」する設計になっているため、厳密なポリシーを求める場合は挙動の見直しを検討。

Migration / Upgrade notes
- 初回導入時は schema.init_schema(db_path) を呼び出して DuckDB のテーブルを作成してください。
- 環境変数は .env/.env.local で管理可能。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- J-Quants API の認証のため JQUANTS_REFRESH_TOKEN が必須です（settings.jquants_refresh_token がこれを参照）。

Contributors
- コードベース自体は本 CHANGELOG 作成時点での解析に基づくため、実際の貢献者クレジットはリポジトリの Git 履歴を参照してください。

---

この CHANGELOG はソースコードの構成・コメント・実装内容から推測して作成しています。実際のリリースノートとして利用する場合は、差異がないか実装者（リポジトリのメンテナ）による確認・追記を推奨します。必要であれば、リリース日や追加の修正項目（run_prices_etl の戻り値修正、テスト追加、strategy/execution 実装予定など）を反映した更新版を作成します。
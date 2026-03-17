# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定化/互換性の方針はセマンティックバージョニングに従います。

現在のバージョン: 0.1.0 — 2026-03-17

## [0.1.0] - 2026-03-17

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージの公開: data, strategy, execution, monitoring。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - .env の上書き制御（override, protected）をサポートして OS 環境変数を保護。
  - Settings クラスを提供し、J-Quants・kabu API・Slack・DB パス・実行環境（development/paper_trading/live）等をプロパティで取得。
  - env / log_level 値検証ロジックと便利なブールプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）・財務（四半期 BS/PL）・マーケットカレンダーを取得する API ラッパー。
  - レート制限対応（固定間隔スロットリング、120 req/min 相当の最小間隔制御）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ（無限再帰防止）。
  - id_token のモジュールキャッシュを保持しページネーション間で共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等性を保証（ON CONFLICT DO UPDATE）。
  - 値変換ユーティリティ（_to_float, _to_int）を追加し不正値や空値に安全に対応。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - デフォルト RSS ソース（Yahoo Finance の business カテゴリ）を定義。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）でリダイレクト先のスキーム/ホストを検証。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査（直接 IP と DNS 解決の両方をチェック）。
    - _urlopen をモック可能にしてテスト容易性を確保。
  - レスポンスサイズ上限を導入（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - テキスト前処理機能（URL 除去・空白正規化）。
  - 銘柄コード抽出機能（4 桁数字の検出と既知銘柄セットによるフィルタ）。
  - DB 保存はトランザクションでまとめ、チャンク挿入・INSERT ... RETURNING を用いて実際に挿入された件数を正確に返却（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数ソースを独立して収集・保存し、銘柄紐付けも一括実行。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - よく使われるクエリに対するインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) により親ディレクトリの自動作成、DDL の実行を行い、冪等にスキーマを初期化。
  - get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新・バックフィル・保存・品質チェック呼び出しを含む ETL フローの骨組みを実装。
  - ETLResult データクラスを追加し、収集結果・品質問題・エラー情報を集約（to_dict により品質問題をシリアライズ可能）。
  - テーブル存在チェックや最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
  - 市場カレンダーを用いた営業日補正ヘルパー（_adjust_to_trading_day）。
  - 差分更新ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の骨組みを実装（差分計算、backfill デフォルト 3 日、_MIN_DATA_DATE による初回ロード）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- RSS パーサーに defusedxml を使用して XML ベースの攻撃を軽減。
- RSS フェッチ時に SSRF を防ぐための複数の防御層を実装（スキーム検査、ホスト/IP の私的アドレス判定、リダイレクト先検査、最大レスポンスサイズチェック、gzip 解凍後のサイズチェック）。
- .env の読み込みは明示的に無効化可能にしてテスト環境や CI での誤動作を防止。

---

備考:
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。将来的なリリースでは変更点を適宜詳細に追記してください。
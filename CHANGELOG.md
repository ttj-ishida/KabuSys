# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従ってバージョニングしています。  
意味的バージョニング(semver)を採用しています。

## [Unreleased]

（現在リポジトリに含まれているコードは初回公開相当の機能群のため、未リリース項目は特にありません。）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名／バージョン管理を追加（__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサを実装（export 形式対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
  - Settings クラスを提供し、J-Quants/ kabu ステーション / Slack / DB パスなど主要設定をプロパティで取得できるように実装。
  - 環境変数値のバリデーション（KABUSYS_ENV の列挙値検査、LOG_LEVEL の検査等）を追加。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - レート制限 (120 req/min) を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライ戦略（指数バックオフ、最大3回、対象ステータス 408/429/5xx）を実装。
  - 401 受信時の自動トークンリフレッシュ（1 回のリフレッシュと再試行）を実装。id_token キャッシュ共有をサポート。
  - ページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する save_* 関数を追加（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC ISO8601 で記録して Look-ahead バイアス対策。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィードから記事を取得し raw_news テーブルへ冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING を活用）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクト時にスキーム/ホストの事前検証を行うハンドラ実装、プライベートIP/ループバック/リンクローカルの遮断。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）を実装。正規化後の SHA-256 ハッシュ（先頭32文字）で記事IDを生成し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字パターン）を実装。
  - bulk 挿入チャンク処理、トランザクション単位でのコミット/ロールバック、INSERT RETURNING による挿入数正確取得を実装。
  - デフォルト RSS ソースに Yahoo Finance（businessカテゴリ）を登録。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py を追加。
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）・インデックスを定義。
  - init_schema(db_path) でディレクトリ作成を含めた初期化とテーブル作成を行うユーティリティを提供（冪等）。
  - get_connection(db_path) で接続を返す関数を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py を追加（ETL の骨組み）。
  - 差分更新戦略（最終取得日を元に差分/バックフィル）を実装。デフォルトの backfill_days = 3。
  - 市場カレンダーの先読み（lookahead）や最小データ開始日設定（_MIN_DATA_DATE = 2017-01-01）を実装。
  - ETLResult dataclass を実装し、フェッチ/保存件数・品質問題・エラーを集約できるようにした。
  - DBテーブル存在チェック、最大日付取得、営業日調整ヘルパー等を実装。
  - run_prices_etl（株価の差分ETL）の骨組みを実装し、jquants_client の fetch/save を利用する設計。

### 変更 (Changed)
- （初回リリースのため過去変更なし。設計方針や API の設計は上記の通り。）

### 修正 (Fixed)
- （初回リリースのため過去のバグ修正履歴はなし。実装上で防御的な入力検証や例外ハンドリングを強化：.env 読み込み時のファイルI/O警告、RSS/XML のパース失敗時の警告とフォールバック等。）

### セキュリティ (Security)
- defusedxml による安全な XML パースを導入（ニュース取得）。
- SSRF 対策:
  - リダイレクト先のスキーム/ホスト検証 (_SSRFBlockRedirectHandler)。
  - _is_private_host によるプライベートアドレス検出（IP 直接判定 + DNS 解決結果の検査）。
- レスポンスサイズ制限と gzip 解凍後チェックを導入（リソース DoS 対策）。
- .env パーサはクォート内のバックスラッシュエスケープに対応し、意図しない展開を抑止。

---

注記:
- 実装は各モジュールで防御的にログ出力・例外処理を行う方針です。ETLは品質チェック（quality モジュール）を組み合わせる想定ですが、quality モジュールの実体はこのスニペットに含まれていません。
- DuckDB の SQL 実行は f-string や直接 SQL 組立が行われる箇所があります（ライブラリ側の仕様に応じて SQL インジェクション等の追加対策が必要な場面があるか確認してください）。本コードではプレースホルダ (?,?,...) を利用する箇所が多く用心されています。
- 今後のリリースでは strategy, execution, monitoring の具現化、ETL の完全なワークフロー・スケジューリング、テストカバレッジ強化を予定してください。
# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に従います。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)
- 廃止 (Deprecated) / 削除 (Removed) は該当があれば記載

注: 以下はリポジトリ内のソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys (日本株自動売買システム) の基礎機能を実装。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env と .env.local の読み込み順制御（.env.local が .env を上書き、OS環境変数は保護）。
  - 行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベル等の取得とバリデーションを提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日次株価（OHLCV）、財務指標（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レートリミッタ実装（120 req/min を固定間隔スロットリングで保証）。
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して 1 回のみリトライ。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を提供。
  - DuckDB へ保存する save_* 関数は冪等性を確保（ON CONFLICT DO UPDATE を使用）。
  - データ取得時の fetched_at を UTC ISO 形式で記録し、Look-ahead bias を防止する設計。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news テーブルへ保存する機能を実装。
  - URL 正規化とトラッキングパラメータ（utm_*, fbclid 等）の除去、記事ID を正規化 URL の SHA-256 (先頭32文字) で生成して冪等性を担保。
  - defusedxml を用いた XML パース（XML Bomb 等の防護）。
  - SSRF 対策: URL スキーム検証 (http/https のみ許可)、ホストがプライベート/ループバック/リンクローカルでないかの判定、リダイレクトハンドラによるリダイレクト先検査。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）を導入。
  - DB 保存はバルク INSERT（チャンク化）、トランザクション、INSERT ... RETURNING により実際に挿入された件数を正確に取得。
  - 銘柄コード抽出機能（4桁数字に対する known_codes フィルタ）と、news_symbols テーブルへの紐付けを一括登録する仕組みを提供。
  - HTTP 操作のテスト容易性のため、_urlopen をモック可能に実装。
- DuckDB スキーマおよび初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）や頻出クエリ向けのインデックス定義を実装。
  - init_schema(db_path) でディレクトリ自動作成と DDL の冪等実行を行い、DuckDB 接続を返すユーティリティを提供。
  - get_connection(db_path) を提供（既存 DB へ接続）。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーなどを集約）。
  - 差分更新のヘルパー（テーブル存在チェック、最終取得日取得、営業日調整）を実装。
  - run_prices_etl など個別 ETL ジョブの基礎を実装（差分取得、backfill_days による後出し修正吸収ロジック、jquants_client の save_* を利用して冪等保存）。
  - 市場カレンダーの先読み日数やデフォルトバックフィル日数等の定数を定義。
- パッケージのモジュール分割（data, strategy, execution, monitoring の公開を __all__ で指定）。

### Security
- ニュース収集での SSRF 対策を実装:
  - URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検出、リダイレクト時の検証を行うカスタムリダイレクトハンドラを導入。
- XML パースに defusedxml を使用して XML 関連攻撃を緩和。
- .env ロードでは OS 環境変数を保護する仕組み（protected set）を採用し、意図しない上書きを防止。

### Performance
- API コールは固定間隔のレートリミッタで制御（120 req/min）。ページネーション時に id_token を共有して余計な認証コールを抑制。
- ニュース保存・銘柄紐付けはチャンク化してバルク INSERT を行い、トランザクションでまとめてオーバーヘッドを削減。
- DuckDB のインデックスを用いて典型的な銘柄×日付スキャンやステータス検索を高速化。

### Notes / Implementation details
- 環境変数取得時に必須キーが未設定だと ValueError を送出する設計（Settings._require）。
- jquants_client の save_* は fetched_at を UTC 形式で保存し、データをいつ取得したかトレース可能にしている。
- news_collector の記事 ID 生成はトラッキングパラメータ除去後の URL をハッシュ化するため、同一記事の重複登録を抑制できる。
- ETL の品質チェック（quality モジュール）との連携設計が示されており、品質問題は収集を中断せず呼び出し元が判断できるようになっている。

### Known issues / TODO
- ETL パイプラインは差分更新や品質チェックの基盤が実装されているが、将来的に次の点を継続実装・改善予定:
  - run_prices_etl / 他 ETL ジョブのエンドツーエンドな統合テストとリトライ/エラーハンドリングの微調整。
  - quality モジュールの各チェック実装（コードベース上で参照されているが、完全実装は別途確認が必要）。
  - モジュール間のエラーレベル・アラート通知（Slack 連携等）の詳細実装と運用ルールの整備。

---

(初期リリースにつき Breaking Changes / Deprecated / Removed の項目はありません)
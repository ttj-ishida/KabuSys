# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
このプロジェクトのバージョン番号はパッケージの __version__（src/kabusys/__init__.py）に従っています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームの基礎モジュールを追加しました。主な内容は以下の通りです。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
  - 空のサブパッケージプレースホルダ: strategy, execution（将来の戦略・発注ロジック用）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env および .env.local ファイル、自環境（OS 環境変数）からの設定読み込みを自動化。
  - プロジェクトルート検出（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない自動読み込み。
  - export KEY=val 形式、クォート中のエスケープ、行コメントの取り扱い等をサポートする .env パーサ実装。
  - 自動ロードの無効化フラグ：KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス：J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供し、未設定時は適切にエラーを送出。

- J-Quants データクライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、マーケットカレンダーの取得関数（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回）とステータス別の振る舞い（408/429/5xx のリトライ等）。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組み。
  - 取得時間（fetched_at）を UTC で記録し Look-ahead Bias を防止。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）で冪等性を確保（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ（_to_float / _to_int）による堅牢な数値パース。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・前処理・DuckDB への保存（raw_news）・銘柄紐付け（news_symbols）を行う統合モジュール。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 防止：URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を超える場合は取得を中止。
    - gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事 ID は URL 正規化（トラッキングパラメータ除去）後の SHA-256 の先頭 32 文字を使用し冪等性を保証。
  - URL 正規化、テキスト前処理（URL除去・空白正規化）、日本株銘柄コード抽出（4桁）機能を実装。
  - DuckDB への保存はトランザクションでまとめて実行し、INSERT ... RETURNING により実際に挿入された件数を返す。
  - run_news_collection により複数ソースを順次処理し、ソース単位での個別エラーハンドリングを行う。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめ、prices_daily, market_calendar, fundamentals, features, ai_scores, signal_queue, orders, trades, positions など主要テーブルを定義。
  - 外部キーやチェック制約（価格 >= 0、サイズ > 0、列挙型制約など）を付与しデータ整合性を強化。
  - 利便性を考慮したインデックス群を作成。
  - init_schema() によりデータベースファイルの親ディレクトリ作成、DDL の冪等実行を行い接続を返す。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新のためのヘルパー（最終取得日の取得、営業日調整など）。
  - run_prices_etl など個別 ETL ジョブの骨組み（差分算出、backfill 設定、品質チェック呼び出しを想定）。
  - ETLResult データクラスにより ETL 実行結果（取得/保存件数、品質問題、エラー）を集約・辞書化可能。

### 改良
- 全体的な設計方針として「冪等性」「セキュリティ（SSRF, XML Bomb 等）」「堅牢なネットワーク/リトライ制御」「DuckDB を用いたトランザクション性」を重視した実装を行いました。
- 各モジュールで詳細なログ出力を追加し、運用時のトラブルシュートを容易にしています。
- ニュース収集は既知のトラッキングパラメータを除去して URL 正規化することで、同一記事の重複挿入を低減します。
- fetch_rss のテスト容易性確保のため、_urlopen を差し替え可能（モック可能）に実装。

### 既知の問題 / 注意点
- run_prices_etl の戻り値シグネチャ不整合: ソースコード末尾（配布されたファイル断片）では
  `return len(records),`
  のように 1 要素のタプルしか返しておらず、ドキュメント上の戻り値 (取得数, 保存数) を満たしていません。リリース前に正しい戻り値（例: `return len(records), saved`）へ修正が必要です。
- strategy/execution サブパッケージは現時点では空のプレースホルダです。戦略実装・発注ロジック・kabuステーション API 統合は未実装。
- DuckDB の SQL 実行で f-string をそのまま使っている部分が存在します（テーブル名等）。現在のコードパスでは引数化されている部分が多いですが、外部入力を直接 SQL 構築に渡すケースがないかレビューを推奨します。
- jquants_client におけるリクエスト関数は urllib を使用した同期実装です。大量データのバックフィルや並列取得を行う場合はスループットの観点から別設計（非同期やバッチ間隔調整）を検討してください。

### セキュリティ関連
- RSS パーシングに defusedxml を採用し XML 関連の攻撃に備えています。
- fetch_rss はリダイレクト先も検査し、プライベート IP へのアクセスを拒否することで SSRF を緩和しています。
- .env 読み込みは既存 OS 環境変数を保護するための protected 処理を行い、.env.local では OS 環境変数を上書きできないよう配慮しています（ただしテスト用途等で KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能）。

---

今後の予定（例）
- run_prices_etl の戻り値/終了処理の修正とカバレッジ向上。
- strategy と execution の具体的な実装（シグナル生成・発注・注文管理・約定処理）。
- 品質チェック（quality モジュール）の実装と ETL パイプラインへの統合（現在は品質チェック呼び出しを想定）。
- 非同期/並列化やバックグラウンドジョブ化による ETL の高速化。
- 追加のログ監視/アラートおよび運用用ドキュメント整備。

もし特に CHANGELOG に追記してほしい点（リリース日付の変更、より詳細な差分、コミット SHA など）があれば教えてください。
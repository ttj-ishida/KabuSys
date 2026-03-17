# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
安定運用上の意図や設計上の注記はコミットメッセージやモジュール docstring から推測して記載しています。

現在のバージョン: 0.1.0

## [Unreleased]
（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能群を実装しました。以下はコードベースから推測される主要な追加点・設計方針・セキュリティ対策です。

### 追加（Added）
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__init__（バージョン 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWDに依存しない自動 .env ロードを実現。
  - export KEY= の形式やクォート、インラインコメントなどを扱う堅牢な .env パーサを実装。
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - 必須設定取得（_require）と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパス、環境・ログレベル判定など）。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制御（固定間隔スロットリング、120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュを提供。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し入力異常に寛容に対応。
  - 取得時刻（fetched_at）に UTC タイムスタンプを付与し、Look-ahead Bias の追跡性を確保。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する処理を実装。
  - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータ除去）。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキームおよびホストの事前検査（プライベートIPやループバックなどを遮断）。
    - DNS 解決結果・直接 IP の判定でプライベートアドレスを検出。
  - レスポンスサイズ制限（デフォルト 10MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出（4桁数字、既知コードセットによるフィルタリング）。
  - DuckDB へのチャンク化されたバルク INSERT（INSERT ... RETURNING）とトランザクションまとめで高効率かつ正確な挿入数取得。
  - public: fetch_rss, save_raw_news, save_news_symbols, run_news_collection などを提供。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを含む。
- スキーマ定義（kabusys.data.schema）
  - DuckDB 用スキーマ定義を提供（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行を行い接続を返す。get_connection() で既存 DB へ接続可能。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得）を行う ETL ヘルパー群を追加（最終取得日取得、営業日調整など）。
  - run_prices_etl 等のジョブ基盤を実装（差分算出、backfill 日数サポート）。
  - ETL 実行結果を表す ETLResult データクラス（品質問題・エラーの集約、シリアライズ機能）を追加。
  - 市場カレンダー先読み、品質チェックフック（quality モジュール参照）を組み込む設計。

### 変更（Changed）
- （初回リリースのため該当なし）設計段階での方針をドキュメント文字列に反映：
  - API レート制御・リトライ・トークン自動更新などの設計原則を明記。
  - ニュース収集のセキュリティ（SSRF、XMLパース、DoS）対策をドキュメント化。
  - ETL の差分更新と backfill 方針を明記。

### 修正（Fixed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- news_collector にて以下の対策を実装:
  - defusedxml を用いた XML パースにより XML 関連の攻撃を緩和。
  - HTTP リダイレクト時の先検査およびホスト検証により SSRF リスクを低減。
  - URL スキーム検証とレスポンスサイズ上限によりローカルファイル参照やメモリDoSを防止。
- jquants_client: トークン管理（キャッシュ・自動リフレッシュ）により認証処理を安全かつ再現性高く実装。

### パフォーマンスと堅牢性（Performance / Reliability）
- API呼び出しのレート制御（固定間隔）と最大リトライ実装により外部 API との安定した連携を目指す。
- 大量挿入時のチャンク化（ニュースやシンボル紐付け）で SQL パラメータ数・文字列長の上限を回避。
- DuckDB 側は ON CONFLICT を活用して冪等性を保証（ETL の再実行安全性）。
- ETL 側でバックフィル日数を指定可能にし、API の後出し修正（修正値）を吸収。

### 開発者向け補足（Inferred）
- 自動 .env ロードはプロジェクトルート探索に基づくため、配布後や CI 環境での動作を考慮して KABUSYS_DISABLE_AUTO_ENV_LOAD によるオフ切替が用意されている。
- テスト容易性を考慮し、news_collector._urlopen はテストでモック可能な実装になっている。
- 型注釈（typing）と詳細な docstring により可読性・保守性を重視したコードベース。

---

メンテナンス情報・既知の注意点
- 現在は initial release（0.1.0）。運用で発見される入力データ差分・外部 API 仕様変更・DB スキーマ変更に対して、後続リリースでの調整が想定されます。
- DuckDB はファイルシステムに依存するため、運用環境の権限・バックアップ方針を設計段階で検討してください。
- 外部 API のレートやエラーコードに関しては J-Quants 側の仕様変更が発生した場合、リトライ/バックオフロジックのチューニングが必要です。

（以上）
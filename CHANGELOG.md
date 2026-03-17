CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、重要なリリースや変更点を記録します。  
このファイルはパッケージのコードベースから推測して作成しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性のある変更）
- Fixed: 修正（バグ修正など）
- Security: セキュリティに関する改善
- Performance: 性能に関する改善
- Other: その他の注意事項

[Unreleased]
------------

(現在未リリースの作業はここに記載します。)

[0.1.0] - 2026-03-17
--------------------

Added
- 初期リリース: KabuSys パッケージ全体を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__="0.1.0"、パブリックモジュールを __all__ で公開 (data, strategy, execution, monitoring)。
- 環境設定モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の優先度制御、OS 環境変数の保護（protected set）に対応。
  - .env パース機能を独自実装（export 形式、クォート／エスケープ、インラインコメント処理をサポート）。
  - Settings クラスを提供し、必要な設定 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等) をプロパティ経由で取得可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑制の仕組みを追加。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジック、判定ヘルパー (is_live, is_paper, is_dev) を実装。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本的な HTTP リクエストラッパー実装（JSON デコード・エラーハンドリング）。
  - レート制限の実装 (固定間隔スロットリング、120 req/min を尊重)。
  - 再試行 (指数バックオフ) ロジックを実装（対象: 408/429/5xx、最大 3 回）。429 の場合は Retry-After を優先。
  - 401 受信時の id_token 自動リフレッシュ（1 回）を実装し、リフレッシュ失敗時は適切に例外を伝搬。
  - ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻を UTC で記録する fetched_at ポイントを付与。
  - 型安全な数値変換ユーティリティ _to_float, _to_int を実装。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS から記事を収集する fetch_rss を実装（content:encoded 対応、description フォールバック、pubDate パース）。
  - defusedxml による XML パース、gzip 解凍対応、応答サイズ上限(MAX_RESPONSE_BYTES=10MB) などの堅牢化。
  - SSRF 対策: URL スキーム検証 (http/https のみ)、プライベートアドレス判定、リダイレクト時の事前検査用ハンドラ (_SSRFBlockRedirectHandler) を実装。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリキーソート）と、それに基づく SHA-256 ベースの記事 ID 生成 (先頭32文字) を実装し、冪等性を確保。
  - テキスト前処理 (URL 除去・空白正規化) と銘柄コード抽出 (4桁パターン + known_codes フィルタ) を実装。
  - DuckDB への保存: save_raw_news（チャンク化・トランザクション・INSERT ... RETURNING を利用して新規挿入 ID を返す）、save_news_symbols、_save_news_symbols_bulk を実装。
  - run_news_collection により複数 RSS ソースを統合収集し、記事保存と銘柄紐付けを一括実行。
  - テスト容易化: _urlopen をモック差し替え可能。
- スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DuckDB 向けのスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、features, ai_scores 等の Feature テーブル、signal_queue, orders, trades, positions 等の Execution テーブルを含む。
  - 適切な CHECK 制約、外部キー、インデックスを定義。
  - init_schema(db_path) でディレクトリ作成を行いスキーマ初期化を冪等に実行、get_connection を提供。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL の骨格を実装。
  - ETLResult dataclass により実行結果・品質問題・エラーを集約して返却。
  - 市場カレンダーに基づいた営業日調整ロジック (_adjust_to_trading_day) を実装。
  - DB の最終取得日を返すヘルパー (get_last_price_date, get_last_financial_date, get_last_calendar_date) を実装。
  - run_prices_etl により差分取得（バックフィル日数）と jquants_client の fetch/save を組み合わせる初期実装を提供（バックフィルデフォルト: 3 日）。
- ロギング/監査
  - 各モジュールにおける情報・警告ログを充実させ、失敗時の詳細ログ出力と例外ハンドリングを整備。

Security
- RSS 処理に defusedxml を採用して XML 関連の脆弱性を軽減。
- 全ネットワーク入出力で URL スキーム検証・プライベートアドレスチェックを実施し SSRF を防止。
- HTTP レスポンスの受信サイズに上限を設け、メモリ DoS を低減。
- J-Quants API 呼び出しにおいて認証失敗時の自動トークンリフレッシュの制御（無限ループ回避）を導入。

Performance
- API レート制御 (固定間隔スロットリング) によりレート超過を防止。
- DB へのバルク/チャンク挿入、INSERT ... RETURNING、ON CONFLICT を利用した冪等保存でオーバーヘッドを削減。
- ニュースの銘柄紐付けをバルクで一括 INSERT することで I/O オーバーヘッドを低減。

Other
- テスト・デバッグ支援:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時に .env の自動ロードを抑止可能。
  - jquants_client / news_collector の一部ポイントでトークン注入や _urlopen の差し替えを想定しており、ユニットテストでのモックが容易。
- DB schema は :memory: をサポート（単体テストや CI 用に便利）。

Known limitations / Notes
- 初期実装段階のため Strategy / Execution / Monitoring の具象実装は含まれておらず、各層のインターフェース基盤とストレージは整備済み。
- run_prices_etl など ETL の一部は「差分算出→取得→保存→品質チェック」を想定した実装骨格を提供。今後、品質チェック (quality モジュール) の具体的チェック実装やエラーハンドリング方針の拡張が必要。
- J-Quants API のエンドポイント仕様や戻り値の細部は実運用での検証に基づき微調整される可能性あり。

Repository / パッケージ利用上の参考
- 主要公開 API:
  - kabusys.__version__
  - kabusys.settings (設定オブジェクト)
  - kabusys.data.init_schema / get_connection
  - kabusys.data.jquants_client.get_id_token, fetch_*, save_* 等
  - kabusys.data.news_collector.fetch_rss, save_raw_news, run_news_collection
  - kabusys.data.pipeline.run_prices_etl, ETLResult

今後の予定（例）
- quality モジュールを実装してETL品質チェックを本格化する。
- Strategy / Execution 層におけるシグナル生成・発注・約定処理の具体実装。
- モニタリング（Slack 通知等）と運用向け CLI / scheduler の提供。

---

注: この CHANGELOG は提供されたコードから推測して作成しています。実際のコミットログやリリースノートが存在する場合は、そちらに基づいて正確な変更履歴を記載してください。
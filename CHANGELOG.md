# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

※ このリポジトリのパッケージバージョンは src/kabusys/__init__.py にある __version__ = "0.1.0" に準拠しています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージの基本構成を追加
  - kabusys パッケージのエントリーポイントと公開モジュールリストを定義（data, strategy, execution, monitoring）。
- 設定・環境変数管理モジュールを追加（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの堅牢化（export プレフィックス、クォート／エスケープ、インラインコメントの扱い）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス等の必須設定をプロパティ経由で取得。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装。
- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用の fetch_* 関数を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - 再試行（指数バックオフ、最大3回）と 401 の自動トークンリフレッシュ対応を実装。
  - get_id_token によるリフレッシュトークンからの idToken 取得処理を実装。
  - DuckDB へ保存する save_* 関数を実装し、ON CONFLICT を用いた冪等性（INSERT ... ON CONFLICT DO UPDATE）を確保。
  - データ変換ユーティリティ（_to_float, _to_int）を実装し、不正な値を安全に扱う。
  - 各操作で fetched_at（UTC ISO 8601 形式）を記録し、データ取得時刻をトレース可能に。
- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し、raw_news テーブルへ保存する処理を実装（fetch_rss, save_raw_news）。
  - 記事IDを正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保。
  - defusedxml を用いた XML パース（XML Bomb 等の対策）、および受信サイズ上限（10MB）・gzip 解凍後サイズ検査（Gzip bomb 対策）を実装。
  - SSRF 対策：URL スキーム検証（http/https のみ）、初回とリダイレクト先ホストのプライベートアドレス検査、リダイレクトハンドラによる事前検証を実装。
  - トラッキングパラメータ（utm_*, fbclid, gclid など）の除去、URL 正規化機能を実装。
  - raw_news へのバルク挿入はチャンク化して単一トランザクションで実行し、INSERT ... RETURNING により実際に挿入された ID を返す。
  - 記事と銘柄コードの紐付け機能（news_symbols）を実装。重複除去・チャンク挿入・トランザクション制御対応。
  - テキスト前処理（URL除去・空白正規化）と、テキストからの4桁銘柄コード抽出ロジックを提供。
- DuckDB スキーマ定義と初期化モジュールを追加（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル定義（DDL）を提供。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、prices_daily, market_calendar, fundamentals 等の Processed テーブル、features / ai_scores の Feature テーブル、signals / signal_queue / orders / trades / positions / portfolio_performance の Execution テーブルを定義。
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックス（検索パターンを想定）を作成。
  - init_schema(db_path) によりディレクトリの自動作成を行い、全DDLを冪等的に実行して初期化する関数を提供。get_connection() で既存DBへ接続可能。
- ETL パイプラインモジュールを追加（kabusys.data.pipeline）
  - 差分更新（最終取得日を確認して新規データのみ取得）を行うヘルパー関数を実装（get_last_price_date 等）。
  - run_prices_etl 等の差分ETL処理骨子を実装（backfill_days による再取得、最小データ開始日の取り扱い）。
  - ETL 実行結果を表現する ETLResult データクラスを実装。品質チェック結果やエラーの集約、辞書化メソッドを提供。
  - ETL 内で使用する市場カレンダー補正（_adjust_to_trading_day）を実装。
- その他ユーティリティ・設計文書への言及を多数実装（各モジュールの docstring に設計方針やセキュリティ考慮点を明記）。

### 変更 (Changed)
- 初版のため過去バージョンからの変更はなし。設計・実装方針をモジュール docstring として明文化。

### セキュリティ (Security)
- RSS/XML 処理に defusedxml を採用して XML 関連攻撃を軽減。
- ニュース取得での SSRF 防止機能を多数実装（スキーム検証、プライベートIP検出、リダイレクト検査）。
- ネットワーク受信バッファに上限を設け、gzip 解凍後もサイズを検査することでメモリ DoS / Gzip bomb に対処。
- .env の読み込みにおいて OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制限・今後の課題 (Known issues / TODO)
- strategy, execution, monitoring パッケージはパスだけ存在し、実際の戦略ロジック・発注処理・監視機能は未実装（将来的な実装対象）。
- quality モジュールは pipeline から参照されているが（品質チェックの設計に言及）、品質チェック実装の詳細は別途提供が必要。
- テストカバレッジ（ユニットテスト / 集約テスト）は未確認のため、ネットワーク依存部分はモック化したテストが必要。
- J-Quants API のレート制御・再試行ロジックは実装済みだが、実運用での微調整（Retry-After の扱い、レートリミッタ精度など）が必要な可能性あり。
- news_collector の DNS 解決失敗時の扱いは「安全側に通過」としているため、運用ポリシーに応じた厳格化を検討。

### 互換性 (Compatibility)
- 初期リリースのため、後方互換性に関する変更はなし。

---

（必要に応じて各関数・DDL の細かな変更履歴を追加できます。ご希望があれば、各モジュール単位でより詳細な CHANGELOG エントリを生成します。）
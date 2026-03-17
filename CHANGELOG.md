CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- なし（次回リリースに向けた未リリース変更はここに記載します）

[0.1.0] - 2026-03-17
--------------------

最初の公開リリース。日本株自動売買システム KabuSys の基盤機能を実装しました。
以下はコードベースから推測できる主要な追加・設計方針・既知の注意点です。

Added
- パッケージ基盤
  - パッケージエントリポイント src/kabusys/__init__.py を追加。__version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を基準に特定）。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト用途）。
  - .env/.env.local の読み込み優先度を実装（OS環境変数を保護しつつ .env.local で上書き可能）。
  - .env 行パーサーの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の必須・既定値・検証ロジックをカプセル化。
  - 環境 (development / paper_trading / live) とログレベルの検証、is_live/is_paper/is_dev のユーティリティプロパティを追加。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（/_BASE_URL = "https://api.jquants.com/v1"）。
  - レート制御（固定間隔スロットリング）を導入して 120 req/min を厳守する _RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1 回まで）と ID トークンのモジュールレベルキャッシュを追加。
  - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB へ保存する冪等的保存関数 save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻（fetched_at）は UTC ISO 形式で記録し、Look-ahead Bias のトレースに配慮。
  - 型変換ユーティリティ _to_float/_to_int を追加（空値・不正値を安全に扱う）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - セキュリティ対応:
    - defusedxml を利用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベートアドレスか判定し拒否、リダイレクト時にも検証する専用ハンドラを導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - URL の正規化とトラッキングパラメータ削除、SHA-256（先頭32文字）による記事 ID 生成で冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）や記事の pubDate パース補助を実装。
  - DB 保存:
    - save_raw_news はチャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING id により、実際に挿入された記事IDを返却。
    - save_news_symbols / _save_news_symbols_bulk による (news_id, code) 紐付けの一括保存（RETURNING による正確な挿入数の取得）。
  - 銘柄抽出: テキスト中の 4 桁数字候補から既知銘柄セットと照合して抽出する extract_stock_codes を実装。
  - run_news_collection: 複数 RSS ソースを横断して収集→保存→銘柄紐付けまで行う統合ジョブ（ソース単位で堅牢なエラーハンドリング）。
- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を一括定義（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions といった Raw テーブルをはじめ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols、features, ai_scores、signals, signal_queue, orders, trades, positions, portfolio_performance などのテーブルを定義。
  - 頻出クエリに対するインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ自動作成→全 DDL とインデックスを冪等的に作成する機能を提供。get_connection() も提供。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約。
  - 差分更新のためのヘルパー関数（テーブル存在確認、最大日付取得、calendar に基づく営業日調整）を実装。
  - run_prices_etl: 差分更新 (backfill_days デフォルト 3 日) を行い、fetch→save を自動で実行するジョブを実装（J-Quants client を利用）。

Security
- RSS パーシングに defusedxml を採用、SSRF 対策、Content-Length/サイズ検査、gzip 解凍後サイズ確認など多層的な防御を実装。
- .env ロード時に OS 環境変数を保護する protected ロジックを導入し、意図しない上書きを防止。

Improved developer ergonomics
- 設定値（DB パス、API ベースURL 等）にデフォルトを設定し、ローカル開発での利便性を向上。
- テスト容易性を考慮した設計:
  - _urlopen をモック可能にして RSS 取得テストを容易化。
  - run_prices_etl 等で id_token を注入可能にして外部依存を切り離しやすく設計。

Fixed
- （初期リリースのため、これまでのコミットに対する注記）

Known issues / Notes
- run_prices_etl の末尾にある return 行が不完全（コード断片: "return len(records), " のように見える）。本来は (取得件数, 保存件数) のタプルを返す設計のため、保存件数を返す実装（例: saved 変数の返却）が必要。リリース直後に修正されるべき箇所としてマーキングされています。
- pipeline モジュールは quality モジュールを参照しますが、該当モジュールの実装（このスナップショット内）は含まれていないため、品質チェック周りは別モジュールの実装を前提としています。
- strategy/, execution/, monitoring/ パッケージはパッケージ構成はあるもののこのリリース時点では具体的実装が未配置（プレースホルダ）。将来的に戦略ロジック・発注実行・監視機能を追加予定。

Deprecated
- なし

Removed
- なし

その他（設計メモ）
- データ取得は「冪等性」と「監査可能性（fetched_at）」を重視して設計されているため、再取得や後出し修正に強い設計になっています。
- API レート制御とリトライ挙動は本番とバッチ処理双方で安全に動作するように制約を組み込んでいます（120 req/min、指数バックオフ、Retry-After の尊重）。
- ニュース収集はスケールや DoS 攻撃を意識してチャンク挿入や最大受信バイト制御を導入しています。

今後の予定（推測）
- run_prices_etl の戻り値不整合修正。
- quality モジュールの実装と ETL 内統合（品質チェック結果に基づく自動アラートやロギング）。
- strategy / execution / monitoring の具体実装（取引戦略、板寄せ・成行/指値発注、Slack による通知等）。
- 単体テスト・統合テストの追加、CI ワークフロー整備。

---

訳注:
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴やドキュメントがある場合はそちらを優先してください。
# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
現時点のリリース履歴は、コードベースから推測して記載しています。

累積リリース
------------

Unreleased
- （なし）

0.1.0 - 2026-03-17
------------------
Added
- 基本パッケージを追加
  - パッケージ名: kabusys
  - __version__ を 0.1.0 に設定し、公開サブパッケージとして data, strategy, execution, monitoring を登録。

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索するため CWD に依存しない。
  - .env 行パーサを堅牢化（export 構文、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応）。
  - 既存 OS 環境変数を保護する protected オプションを導入（.env.local の override 挙動制御）。
  - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や DB パス（DUCKDB_PATH / SQLITE_PATH）、環境種別（KABUSYS_ENV）、ログレベル（LOG_LEVEL）などをプロパティ経由で取得。
  - KABUSYS_ENV、LOG_LEVEL の値検証を実装（許容値以外は ValueError）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（JSON デコード、タイムアウト）。
  - レート制限制御（固定間隔スロットリング）を実装: デフォルト 120 req/min。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象ステータスやネットワークエラーに対してリトライ。
  - 401 Unauthorized 受信時はリフレッシュ処理を自動実行して 1 回だけ再試行（id_token キャッシュと強制リフレッシュ対応）。
  - ページネーション対応の fetch_* 関数を実装:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数を実装（冪等性重視: ON CONFLICT DO UPDATE）:
    - save_daily_quotes: fetched_at を UTC で記録
    - save_financial_statements: 財務データ保存（PK: code, report_date, period_type）
    - save_market_calendar: HolidayDivision を解釈して取引日/半日/SQ 日を保存

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集ロジックを実装（デフォルトソース: Yahoo Finance ビジネス RSS）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - HTTP リダイレクト先のスキーム検証とプライベートアドレス判定（SSRF 対策）。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズを制限（MAX_RESPONSE_BYTES = 10 MB）しメモリ DoS を防止。
    - gzip 圧縮の安全な解凍（解凍後もサイズ上限を検証）。
  - 記事 ID 生成: URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント除去）後に SHA-256 の先頭 32 文字を使用し冪等性を確保。
  - テキスト前処理機能（URL 除去、空白正規化）。
  - テキストからの銘柄コード抽出機能（4 桁数字、known_codes フィルタ）。
  - DuckDB への保存:
    - save_raw_news: チャンク挿入・トランザクション・INSERT ... RETURNING による新規挿入 ID の取得
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをチャンク・トランザクションで保存し、ON CONFLICT で重複を排除して実挿入数を返す

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを定義し、init_schema で一括初期化可能。
    - Raw / Processed / Feature / Execution 層のテーブルを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各種チェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を設定。
    - よく使うクエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - init_schema は db_path の親ディレクトリを自動作成し、":memory:" のサポートを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約可能。
  - スキーマ/テーブル存在チェック、最終取得日の取得ユーティリティ（get_last_price_date 等）を実装。
  - 市場カレンダーを参照して非営業日を最近の営業日に調整するヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl の差分更新ロジック（最終取得日からの backfill 処理、_MIN_DATA_DATE の扱い、fetch→save のフロー）を実装。

- その他
  - data パッケージ内に jquants_client, news_collector, schema, pipeline 等の実装を追加。
  - strategy, execution, monitoring パッケージの雛形を作成（将来の戦略/発注/監視機能の準備）。

Security
- RSS 取得処理に対する複数の SSRF・XML 攻撃緩和策を実装:
  - defusedxml の導入、リダイレクト先のスキーム検証、プライベートホスト判定、最大受信バイト数制限、gzip 解凍後の検査。
- .env 読み込みで OS 環境変数を保護する仕組みを導入（protected set）。

Notes / Known Limitations
- strategy / execution / monitoring はパッケージレベルで用意されていますが、実装はこれから拡張する想定の雛形です。
- ETL パイプラインは差分更新と基礎的な品質チェック呼び出しのフローを整備していますが、品質チェックモジュール（quality）の詳細実装や上位ジョブの統合は別途実装される想定です。
- J-Quants クライアントはネットワークや API のエラー処理を強化していますが、実際の API レスポンスフォーマットの変化や追加エンドポイントには追従が必要です。

ライセンス、貢献、謝辞
- 初期実装に対する貢献者（コードベースの実装者）に感謝します。今後の改善（テスト追加、ドキュメント補強、モニタリング実装等）を歓迎します。

-- End of changelog --
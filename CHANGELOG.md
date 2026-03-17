# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース日はコードベースから推測した初期リリース日を記載しています。  
- 記載内容はソースコードの実装・コメントから推測した機能説明・修正点です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基盤的コンポーネントを実装しました。以下は主な追加点・設計方針・注意点です。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により、CWD に依存しない自動 .env ロードを実装。
  - .env のパース機能（コメント・export プレフィックス・クォート処理・インラインコメントの取り扱い）を実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須設定取得時に未設定で ValueError を投げる _require ユーティリティ。
  - 設定プロパティ（J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル）を実装。環境値検証（有効な env 値・ログレベル）を導入。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ _request を実装。JSON デコード検証、タイムアウト対応。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。再試行対象ステータスや Retry-After の尊重を実装。
  - 401 応答時の自動トークンリフレッシュ（get_id_token）を 1 回のみ行う仕組みを導入。
  - ページネーション対応で日足・財務データを取得する fetch_* 関数を実装。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias 対策。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装（raw_prices, raw_financials, market_calendar）。
  - 型変換ユーティリティ _to_float / _to_int を実装（安全なパース・異常値の扱いを明確化）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存するフル実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバックアドレスの検出、リダイレクト先検査用の _SSRFBlockRedirectHandler を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後のサイズ再チェック。
  - URL 正規化 (_normalize_url) とトラッキングパラメータ除去（utm_ 等）を実装。正規化 URL から記事 ID を SHA-256（先頭32文字）で生成して冪等性を担保。
  - コンテンツ前処理（URL 除去、空白正規化）を実装。
  - RSS の pubDate パース（RFC 2822）とタイムゾーン正規化を実装。パース失敗時は現在時刻で代替し warning を出力。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を使って実際に挿入された記事 ID を返す。チャンク分割とトランザクションで効率化。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けをバルクで保存（ON CONFLICT DO NOTHING + RETURNING）。
  - 銘柄コード抽出ユーティリティ（4桁数字候補を known_codes でフィルタ）を実装。
  - run_news_collection: 複数ソースの独立した取得・保存処理を実装。ソース単位でエラーをハンドリングし、進行を継続。

- データスキーマ / 初期化（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマ（Raw / Processed / Feature / Execution 層）を定義。
  - テーブル DDL を多数定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - インデックス定義（クエリパターンに基づく）を追加。
  - init_schema(db_path) での初期化関数を実装（親ディレクトリの自動作成、冪等の CREATE IF NOT EXISTS）。
  - get_connection(db_path) を提供（初期化は行わない接続取得）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を実装（結果の集約、品質問題とエラーの情報を保持）。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists / _get_max_date）。
  - 市場カレンダーを使った営業日調整ヘルパー _adjust_to_trading_day を実装（最大 30 日遡る）。
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - run_prices_etl を実装（差分ロジック、バックフィル日数の扱い、J-Quants からの取得→保存の流れ）。id_token 注入可能にしてテスト容易性を確保。

- 設計・テスト支援
  - ネットワーク操作（news_collector._urlopen）や認証トークン取得がモック可能な設計にしてテスト容易性を考慮。
  - 例外・ログ出力を多用し障害原因の把握を容易に。

### Changed
- N/A（初回リリースのため過去との互換性に関する変更はありません）。

### Fixed
- N/A（初回リリース）。

### Security
- RSS パーサで defusedxml を採用し XML 関連の脆弱性に対処。
- SSRF 対策を複数導入: スキーム検証、プライベートアドレス判定、リダイレクト時の検査、Content-Length / レスポンス長チェック、gzip 解凍後サイズチェック。
- .env 読み込みは OS 環境変数を protected として上書き防止し、明示的に override された .env.local に限定して上書きできる仕様。

### Performance
- J-Quants API クライアントにレートリミッターを導入し、API レート制限（120 req/min）を守る実装で安定稼働を意識。
- DB 保存はバルク INSERT とトランザクションでまとめ、チャンクサイズ制御による SQL 長・パラメータ数対策を実施。
- DuckDB スキーマに索引を追加し、銘柄×日付等のスキャン性能を改善。

### Notes / Known issues / TODO
- run_prices_etl は基礎的な差分ロジックを実装済みだが、財務・カレンダー ETL や品質チェック（quality モジュールへの依存）との統合は今後の実装・調整が必要。quality モジュールは参照されているが本リリースに含まれる実装範囲はソースの記述に依存します。
- strategy, execution, monitoring パッケージはパッケージ構造としては存在するが、このリリース時点では個別機能の詳細実装が限定的／未実装の可能性があります（__init__ が空）。
- ユニットテスト・統合テストはコード設計時のテストしやすさを考慮して作られている（モック可能な箇所がある）が、テストスイートの有無はソースからは確定できません。

---

作成・更新の履歴は今後のコミットに合わせて本 CHANGELOG を更新してください。
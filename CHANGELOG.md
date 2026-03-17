# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠します。  

安定したリリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-17

### 追加
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージエントリポイント（src/kabusys/__init__.py）を追加。モジュール一覧: data, strategy, execution, monitoring。
  - バージョン情報を `__version__ = "0.1.0"` として定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - `.env` と `.env.local` の読み込み優先順位を実装。OS 環境変数の保護（protected set）に対応。
  - .env パースの堅牢化（export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメント処理）。
  - 主要設定プロパティを提供（J-Quants / kabu ステーション / Slack / DB パス / 実行環境 / ログレベル等）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入（テスト用途）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用の fetch 関数を実装（ページネーション対応）。
  - HTTP レート制御（固定間隔スロットリング）を実装し、120 req/min 制限を守る仕様を導入。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。
  - 401 Unauthorized 発生時の ID トークン自動リフレッシュ（1 回リトライ）を実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスの追跡性を確保。
  - DuckDB へ保存する save_* 関数を実装し、冪等性を保つ（ON CONFLICT DO UPDATE）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS から記事を収集して raw_news に保存するフローを実装（fetch_rss / save_raw_news）。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）によりリダイレクト先のスキームとプライベートIPを検査。
    - ホストのプライベート/ループバック判定（IP 直接判定＋DNS 解決）を実装。
  - defusedxml を利用した XML パース（XML Bomb 等の防御）。
  - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10MB）導入と gzip 解凍後の検査（Gzip bomb 対策）。
  - DB バルク挿入のチャンク化およびトランザクション制御（INSERT ... RETURNING を用いて挿入件数を正確に取得）。
  - テキスト前処理（URL除去、空白正規化）および本文・タイトルから銘柄コード抽出機能（extract_stock_codes）。

- DuckDB スキーマと初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。
  - 各テーブルに適切な型制約、チェック制約、主キー、外部キーを付与（データ品質確保）。
  - よく使われる列に対するインデックス定義を追加（例: code, date, status 等）。
  - init_schema(db_path) でディレクトリ自動作成とスキーマ初期化を行うユーティリティを実装。
  - get_connection(db_path) を提供（既存DB接続取得）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL フローとヘルパー関数を実装。
  - 最終取得日の取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の骨組みを実装（差分算出、fetch->save の流れ、backfill 日数管理、ETL 結果格納用 ETLResult データクラス）。
  - ETLResult に品質チェック結果・エラー一覧を保持し監査ログ等に使える to_dict を追加。

- テスト・運用支援
  - ニュース収集の低レベル HTTP 呼び出し（_urlopen）をモック差し替え可能にしてテスト容易性を確保。
  - jquants_client のトークンキャッシュと id_token 注入によりページネーションやテストの利便性を向上。

### セキュリティ
- RSS 処理における SSRF 対策を実装:
  - スキーム検証（http/https のみ許可）。
  - リダイレクト先のスキームとホストを事前検査。
  - プライベートIPへのアクセス拒否（直接IP・DNS解決の両方で判定）。
- XML パースに defusedxml を利用して XXE / Billion Laughs 等の攻撃を防止。
- .env パースにおいてクォート内エスケープを安全に処理。

### パフォーマンス / 信頼性
- J-Quants クライアントに固定間隔レートリミッタを導入し API 制限を順守。
- リトライ/指数バックオフを備え、ネットワーク不安定時の耐性を向上。
- DuckDB へのバルク挿入をチャンク化して SQL 長・メモリ使用を抑制。
- raw_news / news_symbols / raw_* 保存処理はトランザクションでまとめ、INSERT ... RETURNING を利用して実際に挿入された行数を正確に取得。
- save_* 系関数は冪等性（ON CONFLICT）を確保し、再実行可能に設計。

### 内部（Implementation notes）
- 設定読み込みはプロジェクトルート検出に基づいており、CWD に依存しない実装（パッケージ配布後の動作を意識）。
- jquants_client の内部でページネーション用の pagination_key を管理し、重複ページ防止のため seen_keys を使用。
- 数値変換ユーティリティ（_to_float, _to_int）は不正値耐性を持つ（空文字・不適切フォーマットを None に変換）。
- news_collector は記事ID生成で URL 正規化を行い、トラッキングパラメータの影響を排除。

### 既知の制約 / TODO
- pipeline.run_prices_etl の戻り値の末尾で切れている部分（コード片の末尾）に未完の戻り値整形が見受けられます。実装継続が必要（完全な (fetched, saved) タプルを返すように最終化）。
- quality モジュールは参照されているが本リリースには含まれない可能性があるため、品質チェックの実装・統合が必要。
- strategy / execution / monitoring パッケージはパッケージに含まれるが、詳細な実装は今後追加予定。

---

注: 本 CHANGELOG はソースコード内容に基づいて推測して作成しています。実際のコミット履歴や設計ドキュメントがある場合はそちらを優先してください。
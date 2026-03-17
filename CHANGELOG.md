# CHANGELOG

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog のガイドラインに従っています。

- 名前付け規約: 変更は逆時系列（最新が上）で記載します。
- バージョン番号は semantic versioning（SemVer）を想定しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システムの基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージトップレベルを定義（kabusys.__init__、バージョン 0.1.0）。
  - モジュール公開一覧: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動読み込みをサポート。
  - .env / .env.local の優先度制御（OS 環境変数が保護される仕組み）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env の行パーサーで export プレフィックス・クォート・エスケープ・インラインコメントを考慮した堅牢な解析を実装。
  - Settings クラスで必須設定の取得と検証を提供（J-Quants, kabuAPI, Slack, DB パスなど）。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックと便利なプロパティ（is_live/is_paper/is_dev）。

- J‑Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制限対応（固定間隔スロットリング: 120 req/min）。
  - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx 対応）。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的にトークンを更新して 1 回リトライする仕組み。
  - ページネーション対応（pagination_key の取り扱い）とモジュールレベルの ID トークンキャッシュ。
  - DuckDB へ保存する save_* 関数群（raw_prices / raw_financials / market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を実現。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、不正な文字列や小数の誤切り捨てを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - HTTP リダイレクト時にスキーム/ホストの事前検証を行う _SSRFBlockRedirectHandler による SSRF 対策。
    - ホストのプライベートアドレス判定（IP/ホスト名 → DNS 解決して A/AAAA を検査）。
    - URL スキーム制限（http/https のみ）と受信サイズ制限（MAX_RESPONSE_BYTES, デフォルト 10MB）、gzip 解凍後のサイズ検査（Gzip ボム対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）と SHA-256 ベースの記事 ID 生成により冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存機能（save_raw_news, save_news_symbols, _save_news_symbols_bulk）:
    - INSERT ... RETURNING を用いて実際に挿入された件数を正確に返却。
    - バルク挿入チャンク分割、トランザクションでのまとめて処理、ON CONFLICT による重複スキップ。
  - 銘柄コード抽出ユーティリティ（4桁数字パターンに対し known_codes と突合して抽出）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づく包括的なスキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを含む多数のテーブル定義を実装。
  - features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など実運用を想定した実行関連テーブル群を実装。
  - 頻出クエリ向けインデックスを定義。
  - init_schema(db_path) によるディレクトリ自動作成と冪等的なスキーマ初期化、get_connection の提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジックを実装（DB の最終取得日からの差分取得、backfill_days のサポート）。
  - 市場カレンダーの先読み、最小開始日などの定数を設定。
  - ETL 実行結果を表す ETLResult データクラス（品質チェック結果とエラーの集約、json 互換辞書化）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日補正ロジック（_adjust_to_trading_day）。
  - run_prices_etl の基盤実装（差分算出 → jq.fetch_daily_quotes → jq.save_daily_quotes）。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Security
- news_collector における多層的な SSRF/DoS 対策を導入:
  - リダイレクト時の検査、プライベートアドレスのチェック、受信サイズ上限、defusedxml の採用など。

### Notes / Design decisions
- API 呼び出し時の ID トークンはモジュールレベルでキャッシュし、ページネーション間で共有することで余計な認証呼び出しを削減。
- 保存処理は可能な限り冪等（ON CONFLICT）とし、ETL の再実行を安全にする設計。
- ニュース記事の ID はトラッキングパラメータを除去した正規化 URL のハッシュを使用し、外部リンクのわずかな差異による重複登録を避ける。
- DuckDB をメインのオンディスクデータストアとして想定（デフォルトパスは data/kabusys.duckdb）。":memory:" もサポート。

---

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/
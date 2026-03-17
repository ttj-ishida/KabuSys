# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-17

初期リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。公開 API として data/strategy/execution/monitoring をエクスポート。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない動作を実現。
  - .env/.env.local の読み込み順と上書き制御（OS 環境変数保護）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を提供（テスト用）。
  - .env 行パーサを実装。export プレフィックス、クォート文字列、インラインコメント（#）などに対応。
  - Settings クラスを導入し、J-Quants や kabuステーション、Slack、DB パス、実行環境（development/paper_trading/live）やログレベルの検証付き取得を提供。

- データクライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。株価日足、四半期財務、マーケットカレンダーの取得関数を提供（ページネーション対応）。
  - API レート制御のための固定間隔レートリミッタを導入（120 req/min に対応）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュと一度だけのリトライ処理を実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを可能に。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保。
  - JSON デコード失敗時の明確なエラーメッセージとタイムアウト設定。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを追加。デフォルトで Yahoo Finance のカテゴリ RSS を含むソース定義を提供。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃に対する保護を実装。
  - レスポンス受信サイズ上限（10 MB）を導入し、メモリ DoS 対策を実施。gzip 圧縮の解凍検査（Gzip bomb 対策）対応。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキーム・ホスト検証処理（カスタム HTTPRedirectHandler）
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否
  - 記事ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
  - テキスト前処理（URL 削除、空白正規化）を実装。
  - DuckDB への保存処理：
    - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING による新規挿入 ID の取得
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING、RETURNING により挿入数を正確に計上）
  - 銘柄コード抽出ロジック（4桁数字を候補、known_codes によるフィルタリング、重複排除）。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 向けのスキーマ初期化機能（init_schema）を実装。Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を含む。
  - 各テーブルに適切な型チェック・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
  - パフォーマンス改善のためのインデックス群を作成（頻出クエリに対応）。
  - get_connection による既存 DB 接続取得ヘルパを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計と実装骨子を追加。差分更新（最終取得日に基づく差分算出）、バックフィル（デフォルト 3 日）をサポート。
  - ETL 実行結果を表す ETLResult データクラスを追加（品質チェック結果やエラー一覧を含む）。
  - テーブル存在チェックや最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - 市場カレンダーを考慮した営業日調整機能（_adjust_to_trading_day）。
  - raw_prices/raw_financials/market_calendar の最終取得日取得ヘルパ（get_last_price_date 等）。
  - run_prices_etl（株価差分 ETL、差分取得→保存の流れ）を実装（idempotent 保存を利用）。

### Security
- defusedxml を利用した XML パースにより RSS の XML 攻撃に対処。
- SSRF 対策を多層で実装（初期 URL 検証、リダイレクト時検証、プライベート IP 判定）。
- .env の読み込みは OS の環境変数を保護する仕組みを導入（protected set）。

### Reliability / Robustness
- API 呼び出しのレート制御、再試行（指数バックオフ）、トークン自動リフレッシュを実装し外部 API 依存処理の堅牢化を図った。
- DuckDB への保存処理は冪等（ON CONFLICT）・トランザクション・チャンク化・INSERT RETURNING を活用して一貫性と効率を確保。
- 入力値検証（環境変数の列挙・ログレベル検証、URL スキーム検証、数値変換ユーティリティ）を含む。

### Performance / Efficiency
- レスポンスをチャンク読み込みしサイズ上限を厳格に検査（メモリ消費抑制）。
- RSS / news_symbols の大量挿入はチャンク化してパフォーマンス改善。
- DuckDB 用のインデックスを作成し、銘柄×日付などの検索を高速化。

### Notes / Known limitations
- 初期リリースのため一部モジュール（strategy, execution, monitoring）の実体はまだ空（パッケージエクスポートのみ）。
- quality チェックモジュールの詳細実装は参照されているが、このリリースに含まれるのは pipeline の骨子（quality の具体的なチェックは別実装が期待される）。
- run_prices_etl の戻り値や pipeline の追加ジョブ（財務・カレンダーの差分 ETL 等）は今後拡張を想定。

--- 

今後の予定（例）
- strategy / execution モジュールの実装（シグナル生成〜発注処理の統合）
- 追加品質チェックの実装と ETL の自動化ジョブ化
- モニタリング（Slack 通知や稼働監視）機能の追加
- 単体/統合テストの充実と CI パイプライン構築

以上。
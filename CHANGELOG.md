CHANGELOG
=========

すべての変更は「Keep a Changelog」慣例に従って記載しています。主な方針: 明確なリリース履歴、カテゴリ別（Added / Changed / Fixed / Security / Deprecated / Removed）。

Unreleased
----------
- 開発中: execution/ および strategy/ パッケージは初期のパッケージ構成として存在するが、実装は今後追加予定。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開用の __init__ にバージョン "0.1.0" を設定し、主要サブパッケージ (data, strategy, execution, monitoring) をエクスポート。
- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード実装。
  - .env 読み込みの優先度: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env 行パーサ実装: export プレフィックス、クォート処理、インラインコメント処理等に対応。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス 等のプロパティを提供。値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）や必須チェック（未設定時は ValueError）を実装。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限（デフォルト 120 req/min）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対応）と 401 受信時の自動トークンリフレッシュ（1 回のみ）。
    - id_token のモジュールレベルキャッシュを保持し、ページネーション間で共有。
    - レスポンス取得時に fetched_at を UTC で記録する設計（Look-ahead Bias 対策）。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - 冪等性を担保するため ON CONFLICT を使用した更新ロジック。
    - PK 欠損レコードのスキップとログ出力。
    - 型変換ユーティリティ (_to_float, _to_int) により不正な値を安全に扱う。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード集約モジュールを実装:
    - デフォルトの RSS ソース定義（例: Yahoo Finance）。
    - RSS フィード取得（fetch_rss）と記事前処理（preprocess_text）。
    - URL 正規化（トラッキングパラメータ除去）、記事 ID を正規化 URL の SHA-256 の先頭 32 文字で生成。
    - セキュリティ対策: defusedxml を用いた XML パース、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後サイズチェック、SSRF 対策（スキーム検証、ホストがプライベートアドレスかの判定、リダイレクト検査用ハンドラ）。
    - DB 保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）:
      - チャンク単位での INSERT（パラメータ数制限対策）、トランザクションまとめ、INSERT ... RETURNING による新規追加件数取得。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes）: テキストから4桁銘柄コードを抽出し、known_codes によるフィルタリング。
    - run_news_collection により複数ソースを横断して安全に収集・保存・銘柄紐付けを実行。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw 層の DDL 定義を導入（raw_prices, raw_financials, raw_news, raw_executions 等）。3層（Raw / Processed / Feature）を想定したアーキテクチャ設計に準拠。
- 研究用ファクター・探索 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効ペア < 3）の場合は None を返す。
    - rank / factor_summary: ランク計算（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）。
    - 設計上 pandas 等外部ライブラリに依存せず標準ライブラリのみで実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200日移動平均乖離）を計算。必要行数が満たない場合は None を返す。
    - calc_volatility: 20日 ATR, 相対 ATR (atr_pct), 20日平均売買代金, 出来高比率などを計算。true_range の NULL 伝播を制御して正確なカウントを維持。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損 の場合は None）。
    - いずれも DuckDB 接続を受け取り prices_daily / raw_financials のみを参照。結果は list[dict] で返す。
  - research パッケージ __init__ で主要関数をエクスポート（calc_momentum 等）。
- ロギング / 実運用考慮
  - 各モジュールで詳細なログ出力を追加（INFO/DEBUG/警告レベルの使い分け）。
  - エラー発生時はトランザクションのロールバックと例外再送出を行い安全性を確保。

Security
- RSS 処理における多層防御:
  - defusedxml による XML パースで XML Bomb 等の脅威を低減。
  - SSRF 防止: URL スキームチェック、ホストのプライベートアドレス判定、リダイレクト先の検査を実装。
  - レスポンスサイズ上限を設け、gzip 解凍後のサイズ確認も実施。
- J-Quants クライアント:
  - トークン自動リフレッシュを扱う際に無限再帰を避ける設計（allow_refresh フラグ）。
  - レート制限の尊重（固定間隔スロットリング）。

Fixed
- .env パーサのクォート・コメント処理を堅牢化:
  - export プレフィックス対応、クォート内バックスラッシュエスケープの取り扱い、インラインコメントの正しい判定を実装。
- 数値変換ユーティリティの堅牢性向上:
  - _to_int は "1.0" のような文字列を安全に int に変換し、小数部が存在する場合は None を返して誤って切り捨てることを防止。

Changed
- N/A（初期リリースのため変更履歴はなし）。

Deprecated
- N/A

Removed
- N/A

Notes / Limitations
- research モジュールは pandas 等に依存せず標準ライブラリで実装されているため、大規模データの高速集計や複雑な欠損処理は将来的に外部ライブラリ導入で改善の余地あり。
- schema モジュールは主要な Raw テーブル DDL を定義しているが、Processed / Feature 層の完全な DDL やマイグレーション機能は今後の実装対象。
- execution/strategy/monitoring の詳細実装は今後追加予定（パッケージ構造は用意済み）。

署名
----
この CHANGELOG は、ソースコードの内容からの推測に基づいて作成しています。実際の設計ノートやコミットログと差異がある場合があります。必要ならば追加のコミットメッセージや設計ドキュメントを提供してください。
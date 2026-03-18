# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
現在のバージョンはパッケージの __version__ に合わせて 0.1.0 を初回リリースとして記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース。

### Added
- パッケージ基盤
  - パッケージルートと公開 API を定義（kabusys.__init__）。初期エクスポート: data, strategy, execution, monitoring。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（kabusys.config）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - export KEY=val 形式やクォート・インラインコメント処理に対応する .env パーサ実装。
    - 環境変数の上書き制御（override / protected）とエラーハンドリング。
    - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、実行環境判定等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証。

- データ取得・永続化（J-Quants）
  - J-Quants API クライアントを追加（kabusys.data.jquants_client）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - HTTP リクエスト共通処理（JSON パース、ヘッダ、POST 対応）。
    - リトライロジック（指数バックオフ、最大 3 回。対象ステータス 408/429/5xx）。
    - 401 応答時はリフレッシュトークンによる id_token 自動再取得を行って 1 回だけリトライする仕組み。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を利用。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力データの堅牢な変換を保証。
    - fetched_at に UTC タイムスタンプを記録し、look-ahead bias をトレース可能にする方針を採用。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（kabusys.data.news_collector）。
    - RSS フィード取得（fetch_rss）、記事前処理（URL 除去・空白正規化）、ID（正規化 URL の SHA-256 先頭32文字）生成を実装。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査用ハンドラ、事前ホストのプライベートアドレスチェック、許可スキームの制限（http/https のみ）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化、記事挿入はチャンク化して INSERT ... RETURNING を利用。重複は ON CONFLICT DO NOTHING で防止。
    - 銘柄コード抽出（4 桁数字の正規表現）と DB への紐付け機能（save_news_symbols, _save_news_symbols_bulk）。
    - run_news_collection により複数ソースの収集を統合し、失敗ソースはスキップして継続実行。

- 研究用（Research）機能
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン、1クエリで取得、営業日→カレンダー日バッファ）。
    - スピアマンランク相関（IC）計算 calc_ic（欠損除外、3件未満で None を返す）。
    - ランキング関数 rank（同順位は平均ランク、丸めによる ties 対応）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 研究モジュール群のエクスポートを追加（kabusys.research.__init__）。
    - 標準ライブラリのみでの実装方針（pandas 等に依存しない）。

  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity 指標（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する calc_volatility。
    - Value 指標（per, roe）を計算する calc_value（raw_financials と prices_daily の結合）。
    - DuckDB 上の SQL ウィンドウ関数を組み合わせた実装で、データ不足時には None を返す安全設計。

- スキーマ定義
  - DuckDB 用スキーマ初期化モジュール（kabusys.data.schema）を追加。
    - Raw レイヤーのテーブル定義（raw_prices, raw_financials, raw_news, raw_executions ...）を含む DDL を用意（CREATE TABLE IF NOT EXISTS）。
    - DataPlatform / DataSchema に基づく多層構造設計（Raw / Processed / Feature / Execution）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース収集モジュールでのセキュリティ強化
  - defusedxml による安全な XML パース。
  - SSRF 対策（事前ホストチェック、リダイレクト時の検査、http/https 以外のスキーム拒否）。
  - レスポンスサイズ制限・gzip 解凍後のサイズ検査による DoS/Gzip bomb 対策。
  - URL 正規化でトラッキングパラメータを除去し、ID の冪等性とプライバシー保護を考慮。

- J-Quants クライアントの堅牢化
  - レート制限、リトライ、401 リフレッシュ対応により API 利用時の安定性と安全性を確保。

### Notes / Known limitations
- research モジュールは標準ライブラリのみで実装されているため、大規模データや高度な統計処理は pandas / numpy 等に移行することで性能改善が期待される。
- DuckDB スキーマは一部（Execution 層等）で DDL が途中まで定義されている箇所があり、実運用前に全テーブル定義・インデックス・マイグレーション戦略の確定が必要。
- ニュースの銘柄抽出は単純な 4 桁数字マッチ方式のため、誤検出や文脈依存の抽出漏れが発生する可能性がある。必要に応じて辞書や NLP ベースの抽出に拡張予定。

--- 

（この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴やリリース計画に合わせて適宜更新してください。）
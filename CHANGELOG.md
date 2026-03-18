# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  
安定版リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はここに記載してください）

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値をロードする自動読み込み機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数による自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env ファイルのパーサを実装（コメント、export プレフィックス、クォート、エスケープシーケンス対応）。
  - Settings クラスを実装し、必須設定値の取得・検証を提供（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効値チェック）やユーティリティプロパティ（is_live/is_paper/is_dev）を追加。

- データ取得・永続化（J-Quants クライアント） (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大試行回数、HTTP 408/429/5xx の再試行処理）。
    - 401 レスポンス時の自動トークンリフレッシュと一回のリトライ保証。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による更新を実装。
    - 型安全なユーティリティ _to_float / _to_int を追加。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して DuckDB の raw_news/raw_news_symbols に保存する一連の実装。
    - RSS を安全に取得するための対策を実装:
      - URL スキーム検証（http/https のみ許可）、SSRF 対策（リダイレクト先のスキーム・ホスト検査）。
      - プライベートアドレス検出（IP/ホスト名の DNS 解決による A/AAAA 検査）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES、GZip バウンス対策）。
      - defusedxml を用いた XML パースで XML 攻撃を緩和。
      - トラッキングパラメータ除去・URL 正規化（_normalize_url、_make_article_id）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存はチャンク & トランザクションで実行し、INSERT ... RETURNING を用いて実際に挿入された件数を正確に取得。
    - 銘柄コード抽出ユーティリティ（4桁数字を known_codes でフィルタ）を実装。
    - 総合収集ジョブ run_news_collection を提供（ソースごとに個別エラーハンドリング）。

- 研究用モジュール（kabusys.research）
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、DuckDB SQL による高速取得）。
    - スピアマンランク相関による IC 計算 calc_ic（ランク変換処理と ties の平均ランク対応）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、丸め処理で ties 検出精度を改善）。
  - ファクター計算 (factor_research)
    - calc_momentum：1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility：20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（true range 処理を含む）。
    - calc_value：最新の財務情報と当日の株価から PER/ROE を計算（raw_financials を参照）。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials テーブルのみ参照（外部 API 呼び出し無し）。
  - 研究パッケージのエクスポートを __init__ でまとめて公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw レイヤーの DDL を追加（raw_prices, raw_financials, raw_news など）および初期化用の定義を提供。
  - 型制約・チェック制約（負数禁止など）と主キー定義を含むテーブル定義。

### Security
- news_collector において SSRF 対策・XML パース対策・レスポンスサイズチェックを実装し、外部データ取得の安全性を強化。

### Notes / Design
- 研究・データ取得モジュールは "look-ahead bias" を避ける観点から fetched_at を UTC で記録する設計。
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュ等を備え、実運用を想定した堅牢性を持たせている。
- DuckDB への書き込みは冪等性を保つために SQL 側で ON CONFLICT を使用している。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

開発者向け補足:
- 設定項目や環境変数は kabusys.config.Settings を介して取得してください（例: settings.jquants_refresh_token）。
- DuckDB スキーマやテーブル名（prices_daily, raw_prices, raw_financials, raw_news など）は各モジュールで参照されています。既存 DB を用いる際はスキーマ互換性を確認してください。

（以上）
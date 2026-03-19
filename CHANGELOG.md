# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに従っています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォームのコアライブラリ群を実装しました。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ初期化
  - `kabusys` パッケージの基本エントリポイントを追加（`__version__ = "0.1.0"`、公開モジュール `data`, `strategy`, `execution`, `monitoring` を定義）。

- 環境変数 / 設定管理（kabusys.config）
  - `.env` / `.env.local` 自動ロード機能を実装。プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` から探索して特定。
  - `.env` パーサを実装。`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 既存 OS 環境変数を保護する仕組み（protected set）と `.env.local` による上書き挙動を実装。
  - 必須環境変数取得ヘルパ `_require` と、`Settings` クラスによる型付きプロパティ群を提供（J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DB パス、環境種別・ログレベルのバリデーション等）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制限を守る固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - リトライロジック（指数バックオフ、最大再試行回数、408/429/5xx を対象）と 401 を検知した場合の ID トークン自動リフレッシュを実装。
  - ページネーション対応のフェッチ関数：
    - `fetch_daily_quotes`
    - `fetch_financial_statements`
    - `fetch_market_calendar`
  - DuckDB へ冪等的に保存するためのユーティリティ：
    - `save_daily_quotes`（raw_prices テーブルへの保存、ON CONFLICT DO UPDATE）
    - `save_financial_statements`（raw_financials）
    - `save_market_calendar`（market_calendar）
  - 型変換ユーティリティ `_to_float`, `_to_int`（安全な数値変換ロジック）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集フローを実装（フェッチ、前処理、DB 保存、銘柄紐付け）。
  - セキュリティ・堅牢性対策：
    - defusedxml を用いた XML パース（XML Bomb 等に配慮）。
    - SSRF 対策：リダイレクト時の検査を行うカスタムリダイレクトハンドラ `_SSRFBlockRedirectHandler`、及びホスト/IP がプライベートかどうかを判定する `_is_private_host`。
    - 許可スキームは http/https のみ。初期 URL と最終 URL の両方を検証。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID 生成（正規化 URL の SHA-256 ハッシュ先頭 32 文字）。
  - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
  - RSS パースと記事抽出（`fetch_rss`）と記事保存（`save_raw_news`）：
    - `save_raw_news` はチャンク分割＋単一トランザクションで挿入し、INSERT ... RETURNING で実際に挿入された記事 ID を返す。
    - `save_news_symbols` / `_save_news_symbols_bulk` による記事と銘柄コードの紐付けを実装（チャンク＋トランザクション、ON CONFLICT DO NOTHING、正確な挿入数を返す）。
  - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数字パターンを使用、既知銘柄セットでフィルタ、重複除去）。
  - ラッパー `run_news_collection` により、複数ソースの一括収集と DB 挿入、銘柄紐付けを行う。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 向けのDDL 定義を追加（Raw Layer のテーブル DDL を実装）。
  - テーブル定義（例）:
    - `raw_prices`
    - `raw_financials`
    - `raw_news`
    - `raw_executions`（DDL の一部定義を含む）
  - 各テーブルに対する型制約・チェック制約、主キー定義を含む。

- リサーチ / ファクター系（kabusys.research）
  - 特徴量探索・評価（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns`（単一クエリでまとめて取得、複数ホライズン対応、データ不足は None）。
    - IC（Information Coefficient）計算 `calc_ic`（スピアマンランク相関、結合による欠損排除、有効レコード3未満は None）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸め誤差対策）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム関連 `calc_momentum`（mom_1m/mom_3m/mom_6m、ma200_dev、データ不足は None、DuckDB SQL ベース）。
    - ボラティリティ / 流動性 `calc_volatility`（20日 ATR、相対 ATR、20日平均売買代金、出来高比率、NULL 伝播に注意した true_range の計算）。
    - バリュー `calc_value`（raw_financials から最新の財務データを取得して PER/ROE を計算、EPS が 0/欠損の場合は None）。
  - 設計方針として、すべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番の発注 API 等にはアクセスしないことを明記。外部解析ライブラリに依存しない実装方針。

### Security
- ニュース取得モジュールに SSRF 対策を実装（リダイレクト先スキームチェック、プライベートIP拒否、DNS 解決時の複数 A/AAAA 検査）。
- RSS XML のパースに defusedxml を使用して XML 攻撃に対する防御。
- RSS レスポンスサイズ上限と gzip 解凍後のチェックを導入（DOS / Gzip bomb に対策）。

### Performance / Robustness
- J-Quants クライアントに固定間隔レートリミッタとページネーション共有トークンキャッシュを実装し、安定した大量データ取得に対応。
- save 系関数はチャンク処理やトランザクション、ON CONFLICT による冪等処理を取り入れ、重複挿入や部分失敗に強く設計。
- NewsCollector の DB 操作はチャンクサイズ制御により SQL 長・パラメータ数の上限を考慮。

### Notes
- 研究用ファクター/探索関数は pandas 等に依存せず標準ライブラリ + DuckDB で実装されているため、軽量でテストしやすい一方で大量データ処理時は DuckDB のクエリ最適化に依存します。
- 一部の DuckDB テーブル名（例: prices_daily, raw_financials, raw_prices 等）がコード内で利用されるため、スキーマとテーブル名の整合性に注意してください。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

今後のリリースでは以下のような項目を想定しています（例）:
- Strategy / Execution 層の実装（kabuステーション連携、注文ロジック）
- モニタリング（Slack 通知等）の実装
- テストカバレッジ向上、CI/CD による自動化

もし CHANGELOG に追加してほしい点（例: 各関数の戻り値例、DDL 全体、公開 API の安定化予定等）があれば教えてください。
# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-19

初回リリース。

### 追加
- パッケージ初期化
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`
  - パブリック API: `data`, `strategy`, `execution`, `monitoring` をエクスポートするように設定。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート判定は `.git` または `pyproject.toml`）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - `.env` のパース機構を実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - インラインコメントの扱い（クォート外で `#` の前が空白/タブの場合にコメントと判定）
  - 設定アクセス用 `Settings` クラスを提供（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境/ログレベルなど）。
  - `KABUSYS_ENV` および `LOG_LEVEL` のバリデーションを実装。
  - `duckdb`/`sqlite` のデフォルトパス設定。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - レートリミット制御（120 req/min）を固定間隔スロットリングで実装（内部 `_RateLimiter`）。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 429 の場合は `Retry-After` ヘッダを優先。
  - 401 Unauthorized を検知した場合、自動でリフレッシュトークンから ID トークンを取得して 1 回だけリトライする仕組みを実装（トークンキャッシュを共有）。
  - ページネーション対応で日足データ・財務データを取得 (`fetch_daily_quotes`, `fetch_financial_statements`)、JPX カレンダー取得 (`fetch_market_calendar`)。
  - DuckDB への保存関数（冪等）を実装:
    - `save_daily_quotes` → `raw_prices`
    - `save_financial_statements` → `raw_financials`
    - `save_market_calendar` → `market_calendar`
    - ON CONFLICT DO UPDATE を利用して重複を排除。
  - 入力データの型変換ユーティリティ `_to_float`, `_to_int` を実装（不正値安全処理）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュースを収集して `raw_news` に保存するフローを実装。
  - セキュリティ対策:
    - defusedxml を使った XML の安全なパース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベート IP の拒否。
    - レスポンスサイズ上限（デフォルト 10 MB）を厳格にチェックし、gzip 解凍後も検査。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_* 等）を除去、クエリをソート、スキーム/ホストを小文字化。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を採用し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）ユーティリティを提供。
  - 銘柄コード抽出（4桁数字）と、既知銘柄セットに基づくフィルタリング機能。
  - DB 保存:
    - `save_raw_news` はチャンク単位で INSERT ... RETURNING id により新規挿入 ID を返す（トランザクションでまとめる）。
    - `save_news_symbols` / `_save_news_symbols_bulk` により記事と銘柄の紐付けを一括登録（ON CONFLICT DO NOTHING、INSERT ... RETURNING で実際に挿入された件数を返す）。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - DataSchema.md に基づく初期スキーマ定義（Raw / Processed / Feature / Execution 層）。
  - Raw 層テーブル DDL を実装（例: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions` の定義の一部実装あり）。カラム定義、制約、PRIMARY KEY を含む。

- 研究・特徴量モジュール (`kabusys.research`)
  - feature_exploration:
    - 将来リターン計算 (`calc_forward_returns`) — 複数ホライズン対応、SQL による一括取得。
    - IC（Information Coefficient）計算 (`calc_ic`) — スピアマンのランク相関を実装（ランク付けユーティリティ `rank` を含む）。
    - ファクター統計サマリー (`factor_summary`) — count/mean/std/min/max/median を算出。
  - factor_research:
    - モメンタムファクター計算 (`calc_momentum`) — 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - ボラティリティ/流動性計算 (`calc_volatility`) — 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - バリューファクター計算 (`calc_value`) — raw_financials を参照して PER/ROE を算出。
  - 研究モジュールの API をトップレベルで再エクスポート（`__all__` に factor/feature 関連を追加）。
  - すべて DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照する設計（本番 API へのアクセスなし）。

### 変更
- 設計方針・ドキュメント参照の明記
  - 各モジュールに DataPlatform.md / StrategyModel.md / Research の参照を明記し設計上の制約をドキュメント化。

### 修正（実装上の配慮・安全処理）
- .env パーサ:
  - クォート内のバックスラッシュエスケープやインラインコメント処理を実装して現実的な .env の記法に対応。
- J-Quants クライアント:
  - レート制御とリトライを組み合わせ、429 の `Retry-After` ヘッダを尊重する処理を追加。
  - JSON デコード失敗時にわかりやすい例外メッセージを付与。
  - ネットワーク例外や HTTPError の扱いを明確化。
- NewsCollector:
  - リダイレクト時に事前検証を行うハンドラを実装して SSRF を低減。
  - Content-Length の不正値や gzip 解凍失敗などの異常をログ出力して安全にスキップ。
  - RSS で pubDate がパースできない場合は警告ログを出して現在時刻で代替（raw_news.datetime は NOT NULL）。

### 既知の制約 / 注意事項
- 戦略（strategy）および実行（execution）パッケージは __init__ のプレースホルダが存在するが、個別の戦略ロジックや発注ラッパーは本リリースで最小実装に留まる可能性がある。
- DuckDB スキーマファイルでは Raw 層の DDL は含まれているが、Processed / Feature / Execution 層の完全な DDL は今後の拡張対象。
- research モジュールは標準ライブラリのみで実装しており、大規模データ処理時のパフォーマンスチューニングや pandas 互換のユーティリティは未導入。
- NEWS の URL 正規化・ID 化は既知のトラッキングパラメータ群を除去するが、すべてのトラッキング手法を網羅するものではない。

### セキュリティ
- RSS パースに defusedxml を使用、HTTP/HTTPS スキームの厳格な検証、プライベート IP を拒否する SSRF 対策を導入。
- ネットワーク/外部入力関連のサイズ・型チェックを数箇所で実施し、DoS / 不正データ混入の抑止を行っている。

---

今後の予定（例）
- Processed / Feature / Execution 層の DDL 完全実装とマイグレーション機能追加
- strategy モジュールでの戦略テンプレート実装とバックテストユーティリティ
- monitoring（監視）モジュールの整備（Slack 通知等）
- パフォーマンス改善とテストカバレッジ拡充

（必要であれば、この CHANGELOG をもとにリリースノートやユーザ向け移行手順を追記できます。）
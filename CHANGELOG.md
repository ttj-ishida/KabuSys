# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
タグ付けやリリース管理に利用してください。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。以下の主要コンポーネントと機能を提供します。

### Added
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) により主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数を統合して読み込む自動ローダー（プロジェクトルート検出: .git または pyproject.toml）。
  - .env/.env.local の読み込み順序と `.env.local` の上書きサポート。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
  - POSIXスタイルの .env パーサ（export プレフィックス、クォート文字列のエスケープ、インラインコメント処理など）を実装。
  - Settings クラス：J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルの取得とバリデーション（許容値チェック、is_live/is_paper/is_dev フラグ）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース URL、レート制限（120 req/min）を守る固定間隔レートリミッタ実装。
  - 冪等な取得・保存ワークフロー:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応でデータ取得。
    - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB へ冪等保存（ON CONFLICT ... DO UPDATE）。
  - HTTP リクエストの共通処理：
    - 再試行ロジック（指数バックオフ、最大試行回数）、HTTP ステータス別処理（408/429/5xx の再試行）。
    - 401 Unauthorized を受けた場合のトークン自動リフレッシュ（1 回のみ）と再試行。
    - ページネーション間での ID トークンキャッシュ共有。
  - 入出力の型変換ユーティリティ（_to_float, _to_int）を実装し、CSV/JSON の不正値に耐性を付与。
  - データ取得時に取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能にする設計。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集と DuckDB への保存ワークフローを実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ・堅牢性機能:
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策：HTTP リダイレクト時のスキーム/ホスト検査、事前ホスト検査、プライベート/ループバック/リンクローカル/IP の拒否。
    - 許容スキームは http/https のみ。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）を行い、正規化 URL の SHA-256 先頭32文字を記事IDとして採用（冪等性確保）。
  - テキスト前処理（URL除去、空白正規化）と pubDate の堅牢なパース。
  - DB 保存:
    - save_raw_news：チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk：ニュースと銘柄の紐付けを一括挿入（ON CONFLICT で重複スキップ）し、実挿入数を返す。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字の抽出と known_codes によるフィルタリング、重複除去）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に準拠したスキーマ設計（Raw / Processed / Feature / Execution 層）。
  - Raw 層の DDL 定義を含む（raw_prices, raw_financials, raw_news, raw_executions 等の作成 SQL を定義）。
  - テーブル定義に PK、型チェック（CHECK）、デフォルト fetched_at などを含めた堅牢なDDLを提供。

- 研究用モジュール（Research） (src/kabusys/research/*.py)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns：DuckDB の prices_daily を参照して各ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic：ファクター値と将来リターンの結合から Spearman ランク相関（IC）を計算。無効レコード／小サンプルの扱い（3未満で None）に対応。
    - rank：同順位は平均ランクを採るランク変換。浮動小数誤差を避けるため round(..., 12) を使用。
    - factor_summary：各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 設計上、DuckDB の prices_daily テーブルのみ参照し、本番発注 API へアクセスしないことを明示。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum：mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返却。
    - calc_volatility：20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。true_range の NULL 伝播や cnt による閾値処理を考慮。
    - calc_value：raw_financials から target_date 以前の最新財務情報を取得し PER / ROE を計算（EPS が 0/NULL の場合は PER を None に）。
    - 各計算は DuckDB SQL ウィンドウ関数を多用して効率的に実行し、date=target_date の結果を整形して返す。
  - research/__init__.py で主要 API を再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, および kabusys.data.stats.zscore_normalize の統合）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- ニュース収集周りで SSRF 対策、defusedxml による XML 脆弱性対策、受信サイズ制限（DoS対策）を実装。
- J-Quants クライアントでの堅牢な再試行/トークンリフレッシュ処理により認証失敗や一時的な API 障害の影響を低減。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや計画と差異がある場合があります。追加の修正点や詳細が必要であればソースの他のファイルやコミット履歴を参照して更新してください。
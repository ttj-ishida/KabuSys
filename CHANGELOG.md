Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。

保持方針のヘッダと 0.1.0 の初回リリース情報を含みます。日付は本日（2026-03-18）を使用しています。必要なら日付やバージョンは調整してください。

---
Changelog
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従い、セマンティックバージョニングを採用します。

[Unreleased]
------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-18
-------------------

Added
- 基本パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" に設定。
  - パッケージ外部公開 API として data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - .env パーサを実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理に対応。
  - .env 読み込み時の override/protected 機能を実装（OS 環境変数保護）。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定取得（未設定時は ValueError を送出）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）を Path に変換。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証を実装。
    - 環境フラグ is_live/is_paper/is_dev を提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API レート制限を守る固定間隔レートリミッタ実装（120 req/min 相当の間隔）。
  - リトライロジックを実装（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
  - 401 Unauthorized 受信時にはトークンを自動リフレッシュして1回リトライする仕組みを実装（無限再帰防止フラグ付き）。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB 保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で行う。
    - fetched_at を UTC ISO8601 で記録して Look-ahead Bias を抑制。
  - 型変換ユーティリティ _to_float / _to_int を実装（安全な数値変換と不正値の扱い）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事整形の実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対策）。
    - SSRF 対策: リダイレクト時にスキームとホストの事前検証を行うカスタムリダイレクトハンドラ実装。
    - URL スキーム検証（http/https のみ許可）、プライベート IP/ループバック/リンクローカルの拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）、SHA-256 の先頭32文字を記事 ID として生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS から NewsArticle（TypedDict）を生成する fetch_rss を実装（パースエラー時は安全にログを残して空リストを返す）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING を用いて実際に挿入された記事 ID を返す。チャンク・トランザクション対応。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING、RETURNING を用いて挿入数を正確に取得）。
  - 銘柄コード抽出関数 extract_stock_codes（4桁数字と既知コードセットによるフィルタ）を実装。
  - run_news_collection: 複数 RSS ソースを順次取得して DB に保存し、銘柄紐付けを一括処理する一連処理を実装。各ソースは独立してエラーハンドリング。

- 研究（Research）機能（src/kabusys/research/*）
  - feature_exploration モジュール:
    - calc_forward_returns: DuckDB の prices_daily を参照して forward returns を LEAD を使って計算（複数ホライズン対応、horizons の検証）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なデータがない場合は None を返す。
    - rank: 同順位は平均ランクを返すランク化関数（丸め誤差対策に round(..., 12) を適用）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ機能。
    - これらは外部ライブラリ（pandas 等）に依存せず標準ライブラリと SQL で実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算。true_range の NULL 取り扱いに注意。
    - calc_value: raw_financials と prices_daily を組み合わせ、PER（EPS がある場合）と ROE を計算。最新の報告日以前の財務データを取得するロジックを実装。
  - research パッケージ __init__ で主要関数と zscore_normalize を再エクスポート。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤー向け DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
  - 各テーブルに適切な型、CHECK 制約、PRIMARY KEY を付与してデータ整合性を高める。
  - スキーマ初期化のための基礎を提供。

- パッケージ構成
  - strategy/ および execution/ パッケージの雛形（__init__.py）を追加（現時点では空の初期化）。

Security
- RSS パーシングに defusedxml を使用して XML 関連攻撃に対処。
- RSS フェッチ周りで SSRF 対策（ホスト/リダイレクト検査、スキーム検証、プライベート IP 拒否）を導入。
- 外部 API 呼び出しに対してはレート制限・リトライ・トークン自動更新により安定性と安全性を確保。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Known limitations
- research モジュールの実装は標準ライブラリ依存を優先しており、大規模データ処理時の性能チューニング（ベクトル化等）は今後の課題。
- schema.py に raw_executions の DDL が途中で終わっているように見える箇所があり（ファイル断片の可能性）、実運用前に全テーブル DDL の確認・テストが必要。
- strategy と execution の具象実装（発注ロジック、モニタリング連携など）は未実装のため、本リポジトリは「データ取得・特徴量生成・研究用ユーティリティ」を主目的とする初期版です。

---

変更点の粒度や文言の追加・修正を希望する場合は、重点的に記載したいモジュール（例: ニュース収集の SSRF 部分や J-Quants クライアントのリトライ挙動等）を指示してください。必要に応じて日付やバージョン番号も調整します。
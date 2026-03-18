# Changelog

すべての重要な変更は Keep a Changelog の形式で記載しています。  
このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」のコアコンポーネントを実装しました。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - `kabusys` パッケージの公開モジュール一覧に data, strategy, execution, monitoring を追加。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - プロジェクトルート検出: 現在ファイル位置から `.git` または `pyproject.toml` を探索してプロジェクトルートを特定（配布後も動作）。
  - .env の柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ等に対応）。
  - 設定の必須チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）とバリデーション（KABUSYS_ENV, LOG_LEVEL）。

- データ取得・永続化 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 再試行戦略: 指数バックオフによるリトライ（最大3回）、408/429/5xx を対象にリトライ。429 の場合は Retry-After ヘッダを尊重。
  - 401 応答時はリフレッシュトークンで ID トークンを自動更新して1回リトライ。
  - ページネーション対応でデータを完全取得。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等化を実現。
  - 取得日時（fetched_at）は UTC ISO8601 で記録して Look-ahead Bias をトレース可能に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ向上:
    - defusedxml を用いた安全な XML パース。
    - SSRF 対策: リダイレクト先のスキーム検証、プライベート/ループバックアドレスの検出とブロック（DNS解決時のフォールバックは安全側）。
    - URL スキームは http/https のみ許可。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と Gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事ID の一意化: 正規化した URL の SHA-256 ハッシュ先頭32文字を使用（utm_* 等トラッキングパラメータを除去）。
  - 記事テキスト前処理ユーティリティ（URL 除去・空白正規化）。
  - raw_news テーブルへのバルク挿入（INSERT ... RETURNING）を実装し、実際に挿入された記事IDを返却。トランザクションとチャンク処理で安定性と性能を確保。
  - 記事と銘柄コードの紐付け機能（news_symbols への保存、および一括保存内部関数）。
  - テキスト中からの銘柄コード抽出ユーティリティ（4桁数字、重複排除、既知コードフィルタ）。

- 研究用ファクター計算 (src/kabusys/research/)
  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズンを一括取得・計算）。
    - IC（Information Coefficient）計算: calc_ic（Spearman のランク相関を実装、最小サンプル数チェックを含む）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸め誤差対策で round 使用）。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - これらは標準ライブラリのみで実装され、DuckDB の prices_daily テーブルを参照する設計。
  - factor_research.py
    - Momentum ファクター: calc_momentum（1M/3M/6M リターン、MA200 乖離率。必要データ不足時は None）。
    - Volatility / Liquidity ファクター: calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比率）。
    - Value ファクター: calc_value（raw_financials の最新財務データと当日株価を組み合わせて PER / ROE を算出）。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する設計。
  - research パッケージ __init__ で主要関数と zscore_normalize（data.stats から）をエクスポート。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用 DDL 定義（Raw レイヤーの raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義）を追加。
  - データプラットフォームの3層構造を意識したコメント（Raw / Processed / Feature / Execution）。

### 変更 (Changed)
- （初回リリースのため過去からの変更点は無し）

### 修正 (Fixed)
- （初回リリースのため過去からの修正は無し）

### セキュリティ (Security)
- RSS パーサで defusedxml を採用し XML 関連の脆弱性緩和を実施。
- RSS HTTP クライアントにおいてリダイレクト先のスキーム・ホスト検査を導入し SSRF 対策を強化。
- .env ローダーが OS 環境変数を保護するための protected set を導入し、意図しない上書きを防止。

---

開発者向けメモ:
- 設定は kabusys.config.settings を介してアクセスしてください（例: settings.jquants_refresh_token）。
- DuckDB 接続を渡して各種 fetch/save / factor 計算を呼び出す設計です。各関数は本番発注APIにアクセスしないことを意図しています（研究/データ処理専用）。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください（テスト時に有用）。

--- 

注: 上記はリポジトリ内のコードから推測して作成した CHANGELOG です。実際のリリース日やリリースノートの文言は実プロジェクトの履歴に合わせて調整してください。
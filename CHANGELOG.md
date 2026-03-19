Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更点を記録します。  
フォーマット: https://keepachangelog.com/ja/ を参考に作成しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-19
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0 を導入。
  - パッケージルート /src/kabusys にモジュール構成を定義（data, strategy, execution, monitoring）。
  - __version__ = "0.1.0" を設定。

- 設定/環境変数管理 (kabusys.config)
  - .env / .env.local ファイルをプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。OS 環境変数は保護され、.env.local で上書き可能。
  - .env のパースは export プレフィックス、クォート内エスケープ、インラインコメントなどに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みの無効化が可能。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境モード（development/paper_trading/live）、ログレベルなどを取得・検証するプロパティを実装（不正値時は ValueError）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装。固定間隔のレートリミッタ（120 req/min）を含む。
  - 再試行 (指数バックオフ、最大 3 回)、HTTP 408/429/5xx 系に対するリトライ、429 の Retry-After 優先処理。
  - 401 応答時の自動トークンリフレッシュ（1 回）とトークンキャッシュ共有機能。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (財務四半期データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE を用い重複を排除。
  - データ型変換ユーティリティ (_to_float, _to_int) を実装し、不正データや文字列数値を安全に扱う。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と raw_news, news_symbols への保存機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防止）。
    - HTTP リダイレクト時にスキームとプライベートホストを検査する _SSRFBlockRedirectHandler。
    - 事前および最終リダイレクト先のプライベートアドレス検査。
    - URL スキーム検証（http/https のみ許可）。
    - 最大受信バイト数制限 (MAX_RESPONSE_BYTES = 10MB)、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - コンテンツ処理:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 削除、空白正規化）。
    - 銘柄コード抽出（4桁数字、known_codes でフィルタ）。
  - DB 保存:
    - save_raw_news: チャンク挿入 + INSERT ... RETURNING で新規挿入 ID を返す。トランザクション管理。
    - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けのチャンク挿入（ON CONFLICT DO NOTHING）、挿入数を正確に返却。
  - run_news_collection: 複数ソースの統合収集ジョブを実装（個々のソースでエラーハンドリングして継続）。

- リサーチ（ファクター計算 / 特徴量探索） (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 1日/5日/21日などの将来リターンを一度の SQL で取得。ホライズン検証と結果整形。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算、欠損や ties を考慮。
    - rank: 同順位は平均ランクにするランク計算（丸めで ties 漏れを抑制）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を計算（200日移動平均の欠損ハンドリング）。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を意識）。
    - calc_value: raw_financials から直近財務情報を取得し PER/ROE を計算（price と組合わせ）。
  - 設計方針:
    - DuckDB の prices_daily / raw_financials テーブルのみを参照し外部 API にはアクセスしない（本番発注とは独立）。
    - 標準ライブラリ中心で実装（research の一部は外部ライブラリに依存しないことを明示）。
    - 出力は (date, code) をキーとする dict のリスト。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - raw_layer の DDL を実装（raw_prices, raw_financials, raw_news 等の CREATE TABLE 文を定義）。
  - 各テーブルに適切な型・チェック制約（NOT NULL, CHECK, PRIMARY KEY）を付与。

- 実装上の運用/テスト向けフック
  - news_collector._urlopen はテストでモックして差し替え可能。
  - jquants_client のトークンキャッシュと allow_refresh フラグにより無限再帰を回避。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（実装時に扱った型・NULL の注意点を反映）。

Security
- RSS パースで defusedxml を採用、SSRF 対策、応答サイズ制限、URL スキーム検査等を導入。
- J-Quants クライアントでトークン管理と 401 リフレッシュの安全な制御を実装。

Notes
- strategy/execution/monitoring パッケージは存在を示す (空の __init__.py) が、発注ロジックやモニタリングの具体実装は本バージョンでは含まれていない。
- research 側で zscore_normalize を kabusys.data.stats から import しているが、該当ユーティリティの実体を別モジュールで提供する想定。
- DuckDB への保存・集計は SQL 実行を前提としており、スキーマとデータ整合性（fetched_at, PRIMARY KEY）により Look-ahead bias の追跡・再現が可能。

今後の予定（例）
- strategy/execution の発注実装（kabu ステーション連携）
- monitoring 周りのログ・メトリクス収集
- 追加の研究用ユーティリティ（より多くのファクター、バックテスト基盤）
- 単体テスト・統合テストの充実化と CI ワークフロー

---
作成者注: 上記はソースコードの内容・注釈から推測した変更履歴です。実際のコミット履歴やリリースノートと照合して必要に応じて調整してください。
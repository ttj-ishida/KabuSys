# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはプロジェクトの初回リリース（v0.1.0）の内容をコードベースから推測してまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初期リリース。日本株の自動売買プラットフォーム「KabuSys」のコア基盤を実装しました。以下の主要機能と設計方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - pakage メタ情報: src/kabusys/__init__.py に __version__="0.1.0"、主要サブパッケージを公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数を読み込む自動ローダ実装（優先度: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定（配布後でも動作）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープ処理、インラインコメントの扱い等を実装。
  - 読み込み時に OS 環境変数の保護（protected set）をサポート。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスで設定値をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル判定、is_live/is_paper/is_dev ヘルパ）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 基本クライアントを実装。機能:
    - 株価日足（OHLCV）取得（fetch_daily_quotes）
    - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）
    - JPX マーケットカレンダー取得（fetch_market_calendar）
  - 設計上の特徴:
    - レート制限保護: 固定間隔スロットリングで 120 req/min を保証する _RateLimiter を採用。
    - 再試行ロジック: 指数バックオフ（base=2.0）、最大 3 回リトライ。HTTP 408/429 および 5xx を再試行対象。
    - 401 処理: 401 受信時にリフレッシュを自動で1回試行し再リクエスト（無限再帰を防止）。
    - ページネーション対応: pagination_key を用いた全ページ取得。
    - fetched_at: 取得時刻を UTC ISO8601 で記録（Look-ahead Bias 対策）。
    - DuckDB への保存は冪等性を考慮（ON CONFLICT DO UPDATE）で実装された save_* 関数:
      - save_daily_quotes: raw_prices へ保存（PK: date, code）。
      - save_financial_statements: raw_financials へ保存（PK: code, report_date, period_type）。
      - save_market_calendar: market_calendar へ保存（PK: date）。
    - 型安全な変換ユーティリティ _to_float/_to_int を提供。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを取得し raw_news に保存する実装。
  - セキュリティ・耐障害性設計:
    - defusedxml を用いた XML パースで XML Bomb 等を防御。
    - SSRF 対策: リダイレクト事前検査用 _SSRFBlockRedirectHandler、スキーム検証（http/https のみ）、プライベートアドレス判定 (_is_private_host)。
    - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - URL 正規化: クエリ中のトラッキングパラメータ（utm_ 等）を除去、スキーム/ホスト小文字化、フラグメント除去、並び替え。
    - 記事ID: 正規化URL の SHA-256 の先頭32文字を記事IDとして生成（冪等性確保）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返却。チャンク分割と単一トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存し、挿入数を正確に返却。
  - 銘柄抽出:
    - extract_stock_codes: テキストから 4 桁数字候補を抽出し、known_codes セットでフィルタして重複除去。
  - 統合ジョブ run_news_collection: 複数ソースの収集・保存・銘柄紐付けを実行（ソース毎に独立したエラーハンドリング）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層に分けたスキーマ定義を実装。
  - 主要テーブル（例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など）を含む DDL を提供。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) で親ディレクトリ自動作成のうえ全テーブル/インデックスを作成（冪等）。get_connection() で接続のみ取得。

- ETL パイプライン基礎 (src/kabusys/data/pipeline.py)
  - ETLResult データクラスで ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化。
  - 差分更新のためのユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整（market_calendar を参照、フォールバックあり）。
  - 個別ジョブ run_prices_etl: 差分更新と backfill（デフォルト backfill_days=3）をサポートし、J-Quants から取得→保存（save_daily_quotes）するフローを実装（差分開始日の自動決定ロジック等）。
  - 設計方針: 差分更新単位は営業日ベース、品質チェック（quality モジュール）と連携する想定（品質問題は収集を妨げない挙動）。

- その他
  - data、strategy、execution、monitoring パッケージのプレースホルダ __init__ を配置（将来拡張用）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- ニュース収集での SSRF 対策、defusedxml による XML パース対策、受信サイズ制限、URL スキーム検証などを導入。これにより RSS フィード取込みに関する複数の攻撃ベクトルを軽減。

### 既知の注意点 / 備考
- Settings の一部プロパティは必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を要求します。未設定時は ValueError を送出しますので、.env の用意や環境変数の設定が必要です。
- DuckDB のデフォルトファイルパスは data/kabusys.duckdb（duckdb_path）および data/monitoring.db（sqlite_path）です。init_schema() はデフォルトでは親ディレクトリを自動作成します。
- jquants_client のレート制御は厳格に 120 req/min を想定しており、バルク処理・バックフィルなどで API 制限に注意が必要です。
- run_news_collection は既知コードリスト（known_codes）を与えない場合は銘柄紐付けをスキップします。銘柄抽出のルールは単純な 4 桁数字パターンに基づくため誤抽出の可能性がある点に留意してください。
- ETL パイプラインでは品質チェック（quality モジュール）と連携して問題を検出しますが、品質問題が検出されても収集自体は継続する設計になっています（呼び出し元での判断を想定）。

---

今後のリリース案（推奨）
- strategy / execution モジュールの具体的な戦略・発注実装
- 監視・アラート（Slack 統合）の実装（Slack トークン/チャンネルは既に設定項目あり）
- quality モジュールの実装詳細と ETL 連携の強化
- テストカバレッジ向上（ネットワーク/外部 API のモック、連携テスト）

[0.1.0]: v0.1.0
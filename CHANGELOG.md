CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

注: この CHANGELOG はリポジトリ内のコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-18
--------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。以下はコードベースから推測してまとめた主要な追加項目です。

Added
- パッケージ初期化
  - pakage version: 0.1.0（src/kabusys/__init__.py）
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機構（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env と .env.local の読み込み優先度制御（OS 環境変数を保護する protected ロジック）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ（export 形式、クォート、インラインコメント対応）。
  - 必須設定取得ヘルパ（_require）および Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として要求。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルト DB パス: DUCKDB_PATH と SQLITE_PATH を提供。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）・HTTP ステータス別の挙動制御（408/429/5xx 対応）。
    - 401 時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar。
    - 型変換ユーティリティ: _to_float, _to_int（不正値を安全に None に変換）。

  - ニュース収集（news_collector.py）
    - RSS 取得と前処理パイプライン（fetch_rss, preprocess_text）。
    - XML パースに defusedxml を利用して安全性確保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト検査ハンドラ（_SSRFBlockRedirectHandler）でリダイレクト先のスキーム/プライベートアドレスを拒否。
      - ホストのプライベート/ループバック判定（_is_private_host）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES、gzip 解凍後も検査）および圧縮解凍の耐性チェック。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で一意化。
    - DuckDB への冪等保存:
      - save_raw_news（チャンク挿入、INSERT ... RETURNING で実際に挿入された id を返す）。
      - save_news_symbols / _save_news_symbols_bulk（銘柄紐付け、重複除去、チャンク処理）。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes）: 4桁数字と known_codes に基づく抽出。
    - run_news_collection: 複数 RSS ソースの収集をまとめて実行（ソース単位で失敗を隔離）。

  - DuckDB スキーマ定義（data/schema.py）
    - Raw レイヤーのテーブル DDL（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
    - 初期化用の DDL 定義が含まれており、データレイヤー構造の土台を提供。

- リサーチ用ファクター計算（src/kabusys/research/）
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）。
    - IC（Information Coefficient、Spearman ρ）計算（calc_ic）。
    - ファクター統計サマリー（factor_summary）。
    - ランク計算ユーティリティ（rank）。
    - 設計方針: DuckDB の prices_daily を参照、外部 API にアクセスしない、標準ライブラリのみで実装。
  - factor_research.py
    - モメンタムファクター（calc_momentum）: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）。
    - ボラティリティ / 流動性ファクター（calc_volatility）: atr_20, atr_pct, avg_turnover, volume_ratio。
    - バリューファクター（calc_value）: per, roe（raw_financials と当日の価格を組み合わせて計算）。
    - 各関数はデータ不足時に None を返す設計（安全性重視）。
  - research パッケージ初期化で主要関数をエクスポート（zscore_normalize を data.stats から利用する想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集での SSRF 対策、XML パースの安全化、受信サイズ上限、gzip 解凍後サイズ検査など、多層の安全対策を実装。
- J-Quants クライアントはトークンの自動リフレッシュを適切に行い、401 の無限ループを回避するロジックを採用。

Notes / 注意点
- 研究モジュール（research/*）は外部ライブラリ（pandas 等）に依存しない実装方針。ただし、実運用ではパフォーマンスや利便性のために pandas 等の導入を検討する余地あり。
- DuckDB がランタイム依存として必要（duckdb モジュールをインポート）。
- jquants_client は urllib を使用しており、システムの TLS 設定やネットワーク環境に依存する可能性あり。
- save_* 系関数は DuckDB 接続を受け取り、ON CONFLICT による更新を行うため、DB のスキーマと主キー制約が前提となる。
- Settings に定義された必須環境変数が未設定の場合、ValueError を送出するためデプロイ前に .env を適切に設定してください。
- research パッケージは data.stats.zscore_normalize を参照しているため、data.stats の実装が必要。

Migration / Upgrade
- 初回リリースのためアップグレード手順はありません。既存のユーザーは以下を確認してください:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定。
  - DuckDB スキーマを初期化（schema モジュールを用いる）。
  - 外部 API 利用時は J-Quants の利用規約・レート制限に従う。

Contributors
- コードベースからは明示的な著者情報は得られません。リポジトリのコミット履歴を参照してください。

ライセンス
- コード内にライセンス表記は見つかりません。実際の配布時は LICENSE ファイルを確認してください。

---
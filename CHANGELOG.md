CHANGELOG
=========

すべての重要な変更はこのファイルに記録されます。  
フォーマットは "Keep a Changelog" に準拠します。  

リリース日: 2026-03-18

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
------------------

最初の公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下は主な追加点・設計方針の抜粋です。

Added
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージ公開用のトップレベル __all__ に data/strategy/execution/monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装: コメント・export プレフィックス・シングル/ダブルクォートおよびエスケープに対応。
  - 環境変数の必須チェック `_require` と Settings クラスを提供。以下の主要設定プロパティを提供:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
    - kabu_api_password (KABU_API_PASSWORD)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token, slack_channel_id
    - duckdb_path / sqlite_path（デフォルトパスを提供）
    - 環境判定: env (development/paper_trading/live)、is_live/is_paper/is_dev
    - ログレベル検証 (LOG_LEVEL の正当性チェック)

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - API 呼び出しの固定間隔レート制御（120 req/min 相当の _RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）。
    - 401 受信時の自動トークンリフレッシュを 1 回行う仕組み。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements。
    - JPX マーケットカレンダー取得 fetch_market_calendar。
  - DuckDB への冪等保存ユーティリティ:
    - save_daily_quotes (raw_prices)、save_financial_statements (raw_financials)、save_market_calendar (market_calendar) を実装。
    - 保存は ON CONFLICT (upsert) を用いて冪等化。
    - 型変換ユーティリティ `_to_float` / `_to_int` を提供（不正値は None に変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装:
    - RSS フィード取得（fetch_rss）、記事整形（preprocess_text）、記事ID生成（URL 正規化→SHA-256 先頭 32 文字）。
    - defusedxml を用いた安全な XML パース (XML Bomb 対策)。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、プライベート IP/ホスト拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - DB 保存: save_raw_news（チャンク挿入、トランザクション、INSERT ... RETURNING を使用して新規挿入 ID を返す）、save_news_symbols / _save_news_symbols_bulk（銘柄紐付けの一括保存）。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、known_codes に基づきフィルタ、重複除去）。
    - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を設定。

- データリサーチ (kabusys.research)
  - 研究用途のユーティリティ群を実装・公開:
    - feature_exploration:
      - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一括で計算。
      - calc_ic: スピアマンのランク相関（IC）を計算。レコード不足（<3）や定数分散の場合は None を返す。
      - factor_summary: 指定カラム群の count/mean/std/min/max/median を標準ライブラリのみで計算。
      - rank: 同順位は平均ランクを割り当てる実装（丸めによる ties 検出安定化を含む）。
    - factor_research:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を prices_daily から計算。データ不足時は None を返す。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播を制御）。
      - calc_value: raw_financials から最新財務を取得し PER (close / eps) と ROE を計算（EPS が 0/欠損時は None）。
    - research パッケージの __all__ に主要関数を公開（zscore_normalize は kabusys.data.stats から再エクスポート）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL スクリプトを追加（Raw Layer の raw_prices, raw_financials, raw_news 等の CREATE TABLE 定義）。
  - スキーマの説明（Raw / Processed / Feature / Execution レイヤー）を注記。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集で SSRF・XML Bomb・Gzip Bomb・過大レスポンスからの保護を実装。
- J-Quants クライアントでのトークン刷新とエラーリトライ、レート制御により API 利用の安全性・安定性を向上。

Compatibility / Requirements
- 実行には duckdb、defusedxml モジュールが必要。
- 設計上、研究/特徴量計算モジュールは prices_daily / raw_financials テーブルのみを参照し、本番 API（発注など）にはアクセスしないように設計されています。
- 外部依存は最小限に抑え、feature モジュールは標準ライブラリのみで実装されています（ただし DuckDB 接続が前提）。

Notes / Design Intent
- Look-ahead bias 回避のため、J-Quants データ取得時に fetched_at を UTC で保存。
- DB への保存はできる限り冪等（ON CONFLICT）としており、同一データの重複挿入を避けます。
- .env 読み込みは CWD に依存せずパッケクトファイル位置を基に探索するため、配布後の挙動も安定する設計です。

今後の予定（例）
- Execution レイヤーの発注・約定モデルの実装
- Strategy モジュールの具体的戦略実装およびバックテスト機能
- Feature Layer の拡張（追加ファクター、時系列ラグの自動生成）
- モジュール単体テストと CI の整備

問い合わせ / 貢献
- バグ報告や機能提案は issue を作成してください。仕様や設計コメントはコード内の docstring にも記載しています。
# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
各リリースはセマンティックバージョニングに基づき管理しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。KabuSys のコア機能群を提供します。日本株自動売買システムにおけるデータ収集、特徴量計算、リサーチ用ユーティリティ、設定管理の基盤を含みます。

### 追加 (Added)
- パッケージ初期化
  - pakage version を設定: kabusys.__version__ = "0.1.0"
  - 外部公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード:
    - プロジェクトルートの検出（.git または pyproject.toml を起点）に基づく自動ロード。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
  - 必須環境変数取得用 _require 関数。
  - Settings プロパティ（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev）。
  - env/log_level の値検証（有効値セットを定義）。

- データ取得・保存ライブラリ (src/kabusys/data/)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しユーティリティ（_request）。
    - レート制御: 固定間隔スロットリング（120 req/min のミニマム間隔管理）。
    - 再試行ロジック: 指数バックオフ、最大3回（HTTP 408/429/5xx 対象）。
    - 401 Unauthorized に対する自動トークンリフレッシュ（1回のみ）、および id_token のキャッシュ共有。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）。ON CONFLICT による更新で重複排除。
    - 型変換ユーティリティ _to_float / _to_int（空値・変換失敗の扱いを明確化）。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード取得と前処理の一連処理を提供（fetch_rss, preprocess_text）。
    - セキュア設計:
      - defusedxml を用いた XML パース（XML Bomb 等を防止）。
      - SSRF 対策: URL スキーム検査、リダイレクト先の事前検証、プライベートアドレス判定。
      - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍時のサイズ検査。
      - トラッキングパラメータ除去と URL 正規化、正規化 URL の SHA-256（先頭32文字）で記事IDを生成。
    - DB 保存:
      - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING を用いて新規挿入 ID を正確に取得。
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けを冪等に保存（ON CONFLICT DO NOTHING、チャンク挿入）。
    - 銘柄抽出ユーティリティ extract_stock_codes（4桁コード抽出・既知コードフィルタリング）。
    - デフォルト RSS ソース集を定義（DEFAULT_RSS_SOURCES）。
    - run_news_collection: 複数ソースの取りまとめジョブ。各ソースは個別にエラーハンドリング。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用の初期スキーマ（Raw Layer の例: raw_prices, raw_financials, raw_news, raw_executions の DDL）を定義。
  - DataLayer 設計（Raw / Processed / Feature / Execution の3層記載）。

- リサーチ機能 (src/kabusys/research/)
  - feature_exploration モジュール
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、SQL 集約取得）。
    - IC 計算: calc_ic（スピアマンランク相関、欠損処理、最小レコード条件）。
    - 基本統計: factor_summary（count/mean/std/min/max/median）。
    - ランク付けユーティリティ: rank（同順位は平均ランク、丸めによる ties 考慮）。
    - 設計方針: DuckDB の prices_daily のみ参照、本番 API にはアクセスしない、標準ライブラリのみで実装。
  - factor_research モジュール
    - モメンタム: calc_momentum（mom_1m/mom_3m/mom_6m、MA200乖離）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比）。
    - バリュー: calc_value（raw_financials から最新財務を取得して PER/ROE を算出）。
    - DuckDB を用いたウィンドウ関数・集約による実装。データ不足に対する None の扱いを明確化。
  - research.__init__ で主要 API をまとめて公開（calc_momentum 等と zscore_normalize の再エクスポート）。

- その他
  - data.stats などのユーティリティ関数（zscore_normalize が参照されている点を反映）。
  - strategy、execution パッケージのプレースホルダ（__init__.py を追加、将来の機能追加を想定）。

### 変更 (Changed)
- 初回リリースのため該当なし（初出）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- NewsCollector における SSRF 緩和:
  - リダイレクト先のスキーム検証、プライベートアドレス判定、ユーザエージェント設定、Content-Length/受信サイズ上限など。
- XML の安全パースに defusedxml を採用（XML 関連攻撃対策）。
- J-Quants クライアントで 401 時にトークンを安全にリフレッシュし、無限再帰を防ぐ制御（allow_refresh フラグ）。

### 既知の制約 / 注意点 (Known issues / Notes)
- research モジュールは pandas などの外部依存を避け、標準ライブラリと DuckDB を利用して実装しているため、大規模データ処理ではメモリ／性能面の調整が必要な場合があります。
- calc_forward_returns / calc_momentum 等のホライズンは営業日（連続レコード数）ベースの扱いで、カレンダー日数とは異なります。
- save_* 系関数は DuckDB のテーブルスキーマに依存します。事前にスキーマ初期化を行ってください（schema.py の DDL を使用）。
- news_collector の extract_stock_codes は単純に 4 桁数字を抽出するため、誤検出があり得ます。known_codes 引数でフィルタリングする運用を推奨します。
- jquants_client のレート制御は単一プロセス・単一インスタンスを想定しています。マルチプロセス／分散実行時は外部でのレート調整が必要です。

### 必須環境変数
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- （任意）KABUSYS_ENV（development / paper_trading / live）
- （任意）LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込みを無効化）

### 互換性 (Compatibility)
- 初期リリースのため破壊的変更はありません。将来的にスキーマ変更や API 名変更がある場合は別途 Breaking Changes を明示します。

---

作者・メンテナ: KabuSys 開発チーム  
問い合わせ・バグ報告はリポジトリの Issue にてお願いします。
Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

Unreleased
---------

- （現在未リリースの変更はここに記載します。）

[0.1.0] - 2026-03-19
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下は主要な追加点・設計上の特徴および注意点です。

Added
- パッケージおよびバージョン情報
  - パッケージルート: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。

- 環境設定管理
  - Settings クラスを実装し、環境変数から各種設定を取得（src/kabusys/config.py）。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml の存在）を探索して .env / .env.local を自動読み込み。
    - 読み込み順: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用フック）。
  - .env パーサーは以下に対応:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの扱い（クォート有無に応じて仕様を区別）。
  - 必須環境変数チェック（_require）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は取得時に未設定だと ValueError を送出。
  - 設定のデフォルト値:
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値検証（不正値は ValueError）。

- Data レイヤ
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API ベース URL、ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - RateLimiter によるレート制限（120 req/min）を実装（固定間隔スロットリング）。
    - リトライロジック（最大 3 回、指数バックオフ）を実装。リトライ対象: 408, 429, および 5xx。
    - 401 受信時はトークンを1回自動リフレッシュして再試行（無限再帰を防ぐため allow_refresh フラグあり）。
    - トークンキャッシュをモジュールレベルで保持し、ページネーション間で再利用。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - fetched_at を UTC で記録（Look-ahead bias を防止するトレース用）。
      - INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢化を図る。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS 取得 → 前処理 → DuckDB 保存までの一連処理を実装（run_news_collection）。
    - セキュリティ対策・堅牢性:
      - defusedxml を使用して XML 関連攻撃を低減。
      - SSRF 対応: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック等かを判定してブロック、リダイレクト先も検査。
      - レスポンス上限（MAX_RESPONSE_BYTES=10MB）を導入し、読み込み超過や gzip 解凍後のサイズチェックを行う（Gzip bomb 対策）。
      - User-Agent、gzip ヘッダ対応。
    - URL 正規化:
      - トラッキングパラメータ（utm_*, fbclid など）を除去、スキーム/ホストを小文字化、フラグメント削除、クエリをソート。
      - 正規化 URL の SHA-256（先頭32文字）を記事 ID として使用し冪等性を担保。
    - 保存処理:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID を返却。チャンク処理＆単一トランザクションで実行。
      - news_symbols および _save_news_symbols_bulk: 記事と銘柄の紐付けを重複排除してチャンク挿入（ON CONFLICT DO NOTHING RETURNING を使用）。
    - テキスト前処理（URL 除去・空白正規化）、RSS pubDate の堅牢なパース（UTC で正規化、パース失敗時はログ出力して現在時刻で代替）。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し known_codes でフィルタ（重複除去）。

  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - Raw 層テーブル定義の DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の作成文を含む）。
    - 各テーブルに主キー制約や型チェックを設定（負の値などを防止する CHECK）。

- Research レイヤ
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）
      - 単一クエリで複数ホライズンを同時取得、ホライズン閾値チェック（1〜252 営業日）。
    - Information Coefficient（IC）計算（calc_ic）
      - スピアマンのランク相関を実装し、データ不足や定数分散を考慮して None を返す場合がある。
      - 内部で rank 関数（同順位は平均ランク）を実装（丸め処理により ties 検出の安定化）。
    - ファクター統計サマリー（factor_summary）
      - count/mean/std/min/max/median を算出（None は除外）。
    - 設計方針: DuckDB の prices_daily のみ参照、pandas 等の外部ライブラリに依存しない純 Python 実装。

  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（calc_momentum）:
      - mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離率）を算出。データ不足時は None。
    - Volatility / Liquidity（calc_volatility）:
      - 20 日 ATR（atr_20）、ATR の相対値（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を算出。true_range 計算において high/low/prev_close が NULL の場合は NULL を伝播させることでカウントを正確に管理。
    - Value（calc_value）:
      - raw_financials から target_date 以前の最新財務データを取得し PER（price / EPS）、ROE を計算（EPS が 0 や NULL の場合は None）。
    - 設計方針: DuckDB の prices_daily / raw_financials のみ参照、戦略や本番 API にはアクセスしない。出力は (date, code) をキーにした dict のリスト。
  - research パッケージのエクスポートを整備（calc_momentum 等を __all__ に追加）。

Security
- 外部入力（.env、RSS、外部 API）に対する堅牢性向上:
  - .env のパースでエスケープ・クォートを正しく処理。
  - RSS フェッチで SSRF 対策、レスポンスサイズ制限、defusedxml による XML 攻撃対策。
  - J-Quants クライアントのトークン再取得は 401 の場合に限定し、無限ループを防止。
  - DuckDB への保存において入力チェック（NULL / PK 欠損行のスキップ）を行い、不正データ挿入を減らす。

Notes / Limitations
- 依存の最小化:
  - research モジュールは pandas 等に依存しない設計（標準ライブラリ + duckdb）。
- 一部モジュールは placeholder（空の __init__）:
  - execution／strategy パッケージの初期化子は存在するが具体的な実装は別途追加予定。
- スキーマ定義は Raw 層を中心に実装済み。プロセス層・特徴量層・実行層の追加 DDL は今後の追加対象。
- DuckDB を想定した SQL（ウィンドウ関数、ROW_NUMBER 等）に依存するため、互換性のある環境が必要。
- ニュースの銘柄抽出は単純な 4 桁数字マッチに依存しているため誤抽出の余地あり（known_codes によるフィルタリング推奨）。

Breaking Changes
- 初期リリースのため該当なし。

How to upgrade
- 新規インストール時は必要な環境変数を設定してください（JQUANTS_REFRESH_TOKEN 等）。.env/.env.local をプロジェクトルートに置くことで自動読み込みされます。
- 自動ロードを抑止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- 本リリースはプロジェクトの基盤実装を提供します。今後、execution（発注ロジック）や strategy（ポジション管理）等の実装を順次追加予定です。
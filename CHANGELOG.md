# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、与えられたコードベースの実装内容から推測して作成した初期リリースの変更履歴です。

全般的なバージョン命名規則: MAJOR.MINOR.PATCH

## [0.1.0] - 2026-03-18
初回公開リリース — 日本株自動売買システム（KabuSys）の基盤機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を登録。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を起点に探索して自動的に .env/.env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサーは以下の形式に対応:
    - コメント行、先頭 "export " プレフィックス、クォート（シングル/ダブル）付き値、インラインコメントの扱い等。
    - 値のエスケープ（バックスラッシュ）に対応。
  - 必須環境変数チェック (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等) を行う _require 関数。
  - 設定検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ有効。
    - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のみ有効。

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリングによる RateLimiter を実装。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (財務四半期データ)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - 冪等保存用の DuckDB 保存関数:
      - save_daily_quotes → raw_prices テーブルへ ON CONFLICT DO UPDATE による upsert。
      - save_financial_statements → raw_financials テーブルへ upsert。
      - save_market_calendar → market_calendar テーブルへ upsert。
    - リトライロジック:
      - 指数バックオフ、最大リトライ回数 3、408/429/5xx を対象にリトライ。
      - 401 を受けた場合、リフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ID トークンのモジュールレベルキャッシュを実装し、ページネーション等で共有。
    - 取得結果の fetched_at を UTC で記録（Look-ahead Bias の追跡を想定）。
    - 変換ユーティリティ (_to_float, _to_int) を提供（堅牢な型変換処理）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードを収集して raw_news / news_symbols に保存するモジュールを実装。
  - セキュリティおよび耐障害設計:
    - defusedxml を用いた XML パース（XML Bomb 等に備える）。
    - SSRF 対策: URL スキーム検証（http/httpsのみ）、リダイレクト時のホスト検証、プライベートIP拒否。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍時の再チェック。
    - HTTP リダイレクト検査用ハンドラを実装して、リダイレクト先も安全に検証。
  - テキスト前処理:
    - URL 除去、空白正規化を行う preprocess_text。
    - URL 正規化とトラッキングパラメータ（utm_* など）の除去。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使って実際に挿入された記事IDを取得。チャンク処理 / 単一トランザクション実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク挿入（チャンク化）して正確に挿入件数を返す。
  - 銘柄抽出:
    - extract_stock_codes によるテキスト内の 4 桁銘柄コード抽出（known_codes によるフィルタリング・重複除去）。
  - run_news_collection: 複数ソースからの収集を統括し、個別ソースの失敗は他ソースに影響しない設計。

- データスキーマ (kabusys.data.schema)
  - DuckDB 向けのスキーマ定義（Raw 層）を実装（DDL 定義）。
    - raw_prices, raw_financials, raw_news, raw_executions（部分実装が含まれる）などのテーブル定義を追加。
  - テーブル定義には型制約や CHECK 制約、PRIMARY KEY を明記して整合性を担保。

- 研究（Research）機能 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB のウィンドウ関数で計算。
    - calc_volatility: 20 日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（report_date<=target_date の最新行を JOIN）。
  - feature_exploration:
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位の平均ランク化（丸め誤差対策の round を適用）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出。
  - research パッケージの __init__ で主要関数群を公開。

- その他
  - strategy と execution パッケージの初期化ファイル（空の __init__.py）を追加（将来の拡張ポイント）。

### 変更 (Changed)
- （初回リリースのため過去の変更履歴なし）

### 修正 (Fixed)
- （初回リリースのため過去の修正履歴なし）

### セキュリティ (Security)
- ニュース収集に関する複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト監査）。
  - レスポンスサイズ制限および Gzip 解凍後のサイズ検査（DoS対策）。
- J-Quants クライアントは認証トークンの自動更新やリトライ制御を備え、誤った認証情報や一時的な API 障害への復元性を向上。

### パフォーマンス (Performance)
- DuckDB 側の集約・ウィンドウ関数を活用し、可能な限りデータ集計を DB 側で実行する設計。
- J-Quants の API 呼び出しに固定間隔スロットリングを導入し、レート制限を遵守。  
- ニュース保存や銘柄紐付けはチャンク単位でバルク INSERT を行い、トランザクション回数を削減。

### 既知の制限 / TODO
- strategy および execution パッケージはまだ具体的な戦略ロジック／発注ロジックを実装していない（拡張予定）。
- DataLayer の一部（例: schema 内の execution テーブルの続きなど）はファイル断片により未完の箇所がある可能性。
- research モジュールは外部依存（pandas 等）を使わず標準ライブラリで実装されているため、大規模データでの効率化は今後の課題。

---

今後のリリース案:
- 0.2.0: strategy 実装、execution 発注ラッパー、監視/通知機能の統合。
- 0.2.x: DuckDB マイグレーション/インデックス追加、より詳細なテストカバレッジ確保。
- 1.0.0: 安定 API 確定、ドキュメント整備、公開リリース。

（この CHANGELOG はソースコードの実装内容から推測して生成しています。実際のコミット履歴やリリース日時とは異なる可能性があります。）
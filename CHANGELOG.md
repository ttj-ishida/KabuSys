# Changelog

すべての注目すべき変更をこのファイルに記録します。
このファイルは「Keep a Changelog」方式に準拠しています。

現在のバージョン: 0.1.0 — 2026-03-18

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能群を実装しました。
主に以下の領域を含みます: 設定管理、データ取得/保存、RSSニュース収集、ファクター計算（リサーチ用）、DuckDB スキーマ定義、およびパッケージ公開インターフェース。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名、バージョン定義（__version__ = "0.1.0"）。
    - 公開モジュール一覧 __all__ に data, strategy, execution, monitoring を登録。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パースの堅牢化:
      - export KEY=val 形式対応、クォート内のバックスラッシュエスケープ対応、行内コメントの取り扱い改善。
    - Settings クラスを提供:
      - J-Quants / kabu ステーション / Slack / DB パス等のプロパティ（必須変数は _require で検証）。
      - KABUSYS_ENV の妥当性検査（development, paper_trading, live）。
      - LOG_LEVEL の妥当性検査（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
      - is_live / is_paper / is_dev のユーティリティプロパティ。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - Raw 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news 等）。
    - スキーマ初期化用モジュール（DataSchema.md に基づく設計）。
    - 基本的な型・制約（NOT NULL, CHECK, PRIMARY KEY）を付与しデータ整合性を担保。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API ベースの HTTP ユーティリティ実装（urllib ベース）。
    - レート制限制御（120 req/min）を固定間隔スロットリングで実装する _RateLimiter。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）。
    - 401 発生時はリフレッシュトークンによる自動トークン再取得を一度だけ実行してリトライ。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes (日足)、fetch_financial_statements (財務)、fetch_market_calendar (JPX カレンダー)。
    - DuckDB への保存関数（冪等性を考慮）:
      - save_daily_quotes: raw_prices への挿入（ON CONFLICT DO UPDATE）。
      - save_financial_statements: raw_financials への挿入（ON CONFLICT DO UPDATE）。
      - save_market_calendar: market_calendar への挿入（ON CONFLICT DO UPDATE）。
    - ユーティリティ関数:
      - _to_float / _to_int: 入力値を安全に変換するヘルパー。空値や不整合な数値文字列を None と扱う。

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と前処理、DuckDB への冪等保存ワークフローを実装。
    - セキュリティ/堅牢化:
      - defusedxml を用いた XML パース（XML Bomb 等の対策）。
      - SSRF 防止のためリダイレクト検査・ホストのプライベートアドレスチェック（_is_private_host）。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック。
      - リダイレクト毎にスキーム/ホストを検証するカスタム RedirectHandler。
    - 正規化と重複制御:
      - URL 正規化（トラッキングパラメータ除去、キーソート）と SHA-256 の先頭32文字で記事IDを生成。
      - 記事のテキスト前処理（URL除去、空白正規化）。
    - DB 保存の最適化:
      - INSERT ... RETURNING を用いて実際に挿入された新規記事IDを取得する実装。
      - チャンク化（最大 _INSERT_CHUNK_SIZE）と単一トランザクションでのコミット/ロールバック処理。
    - 銘柄コード抽出:
      - 4桁数字パターンを候補にし、known_codes に基づいてフィルタリング（重複除去）。
    - 統合ジョブ:
      - run_news_collection: 複数ソースの収集 → raw_news 保存 → 新規記事のみ抽出して銘柄紐付けを行う一連処理を実装。

- リサーチ（ファクター/特徴量探索）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: DuckDB の prices_daily テーブルを参照して複数ホライズンのリターンを一度に取得する SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: ファクターレコードと将来リターンを結合して Spearman（ランク相関）を計算。データ不足時は None を返す。
    - ランク関数（rank）: 同順位は平均ランクに処理。丸め（round 12 桁）で ties 判定の安定化。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出（None 値を除外）。
    - 標準ライブラリのみでの実装（pandas 等に依存しない設計）。
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value 等の定量ファクターを DuckDB（prices_daily / raw_financials）から計算する関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）。データ不足は None。
      - calc_volatility: atr_20（20日 ATR平均）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日/平均出来高）。
      - calc_value: per（株価 / EPS、EPSが0や欠損なら None）、roe（最新財務データ）。raw_financials から target_date 以前の最新レコードを取得。
    - スキャン範囲やウィンドウサイズ（21/63/126/200/20 日等）を定数化し、SQL ウィンドウ関数で効率的に算出。
  - src/kabusys/research/__init__.py
    - 主要 API を再エクスポート（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize）。

- 空のパッケージ初期化ファイル（将来の拡張用）
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
    - 将来の実行・戦略モジュールのエントリポイントを準備。

### 変更 (Changed)
- （初回リリースのため過去の変更はありません）

### 修正 (Fixed)
- （初回リリースのため過去の修正はありません）

### セキュリティ (Security)
- news_collector: defusedxml の導入や SSRF チェック、レスポンスサイズ上限、gzip 解凍後の再検査など、多層的な防御を追加。
- jquants_client: トークン自動リフレッシュは allow_refresh フラグで無限再帰を防止。

### 注意事項 / マイグレーションノート
- 環境変数:
  - 必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings のプロパティ参照時に _require により ValueError を投げます。リリース前に .env を用意してください（.env.example を参照することを推奨）。
  - 自動 .env ロードはプロジェクトルートを .git または pyproject.toml で検出します。パッケージ配布後やテスト環境で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - 初回起動時にスキーマ初期化処理を必ず実行してください（DDL の実行によりテーブルが作成されます）。
- J-Quants API:
  - レート制限（120 req/min）とリトライ設定を組み込んでいますが、上流 API の仕様変更があった場合は _MIN_INTERVAL_SEC やリトライ対象コードの見直しが必要です。
- NewsCollector:
  - 記事IDのハッシュは正規化後の URL に基づき先頭32文字を使用します。将来的に ID 長やハッシュ方式を変更すると冪等性に影響します。

---

将来的には execution（発注/約定/ポジション管理）や strategy（売買ロジック）の実装を追加し、本番稼働／バックテストのサポートを拡充する予定です。必要であれば次のリリースノート案や追跡すべき改善点（例: テストカバレッジ、型注釈の強化、pandas を用いた高速集計の optional サポートなど）も作成します。
# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を記載します。  
フォーマット: https://keepachangelog.com/ja/ に準拠しています。

全般的な記載は、与えられたコードベースの実装内容から推測して作成しています。

## [Unreleased]
- （予定・未リリースの変更点をここに記載）

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下は本リリースで追加された主な機能、設計上の方針、重要な仕様です。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイント `kabusys` を実装。`__version__ = "0.1.0"` を設定し、トップレベルの公開モジュールとして `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して自動ロード。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env パーサ実装（引用文字列、export プレフィックス、インラインコメントの扱い等をサポート）。
  - Settings クラスを提供（プロパティベースで各設定値を取得）。
    - J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定などをプロパティで取得。
    - 必須キー未設定時に ValueError を送出する `_require` ヘルパー。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証（許可値チェック）。
    - デフォルト値（例: KABU_API_BASE_URL、DUCKDB_PATH、PID_FILE_PATH 等）を提供。

- データ層（kabusys.data）
  - ETL パイプライン基礎
    - `pipeline.ETLResult` データクラスを公開（`data.etl` 経由で再エクスポート）。
    - ETL の設計方針・バックフィル・品質チェックの枠組みを実装（差分取得、idempotent 保存、品質問題の収集など）。
  - カレンダー管理（market_calendar）
    - 市場カレンダー更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、保存）。
    - 営業日判定ユーティリティ:
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB 未取得時は曜日ベースでフォールバックする堅牢なロジックを実装。
    - 最大探索日数・バックフィル・健全性チェックなどを導入。

- 研究・リサーチ（kabusys.research）
  - ファクター計算モジュールを実装:
    - `calc_momentum`：1M/3M/6M リターン、200日MA 乖離など。
    - `calc_volatility`：20日 ATR、相対 ATR、平均売買代金、出来高比率等。
    - `calc_value`：PER/ROE（raw_financials と prices_daily を組み合わせ）。
  - 特徴量探索ユーティリティ:
    - `calc_forward_returns`：将来リターン計算（任意ホライズン、入力検証あり）。
    - `calc_ic`：スピアマン（ランク相関）ベースの IC 計算。
    - `factor_summary`：基本統計量（count/mean/std/min/max/median）。
    - `rank`：値→ランク変換（同順位は平均ランク）。
  - `zscore_normalize` は `kabusys.data.stats` から再エクスポート。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント（銘柄別）スコアリング (`news_nlp.score_news`)
    - 対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で記事を集約。
    - 銘柄ごとに記事を最大件数・最大文字数でトリムして結合。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信（バッチサイズ 20）。
    - レスポンス検証・数値化・±1.0 クリップ・DuckDB への冪等的書き込み（DELETE→INSERT）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で regime_score / regime_label（bull/neutral/bear）を算出。
    - マクロニュースの抽出（マクロキーワードリストに基づくタイトル検索）と LLM 呼び出し（gpt-4o-mini）で macro_sentiment を取得。
    - スコア合成と ±1.0 クリップ、しきい値でラベル判定（BULL_THRESHOLD/BEAR_THRESHOLD）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - ルックアヘッドバイアス防止のため、内部で date.today() を直接参照しない設計。

- ロギングと堅牢性
  - 各所で WARNING/INFO/DEBUG ログ出力を実装。
  - API 呼び出し失敗時のフォールバックやリトライ、トランザクションのROLLBACK保険等を実装。

### 変更 (Changed)
- （初版のため既存リリースに対する変更はありません）

### 修正 (Fixed)
- （初版のため修正履歴はありません）

### セキュリティ (Security)
- OpenAI API キー等の機密情報は環境変数経由で参照する方式を採用し、設定不備時は例外で明示する実装。

### 設計上の注記 & 既知の仕様
- ルックアヘッドバイアス対策:
  - ニュース/レジーム/ファクター計算いずれも内部で datetime.today()/date.today() を参照せず、外部から渡された target_date に基づいて計算する。
- DuckDB 依存:
  - 多くの処理は DuckDB 接続を受け取り、SQL ウィンドウ関数や executemany を利用して処理する設計。
  - DuckDB バージョン差異（例: executemany の空リスト扱い、配列バインドの互換性）に配慮した実装がされている。
- フェイルセーフ方針:
  - 外部 API の一時障害時は該当部分をスキップまたはゼロ値でフォールバックし、プロセス全体を停止させない設計。
- .env パーサは shell 風の記法（export プレフィックス、シングル/ダブルクォート、エスケープ）に対応しているが、完全な .env 仕様互換性は実装上の差異がある可能性あり。

---

今後のリリースでは、strategy / execution / monitoring の発注周り・モニタリング・運用用 CLI やテストカバレッジ、ドキュメントの追加などが想定されます。必要であれば、本 CHANGELOG を元に各モジュール別の詳細変更点（関数仕様・引数・返り値など）を追記します。
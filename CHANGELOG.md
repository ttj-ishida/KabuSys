# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースから実装内容を推測して作成した初期の変更履歴です。

フォーマット: [Unreleased] → 今後の変更、[0.1.0] → 初回リリース

---

## [Unreleased]

- なし（初期リリースのみ。今後の差分はここに記載）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として定義。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で宣言。

- 環境設定 / .env 読み込み（kabusys.config）
  - .env と .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - export KEY=val 形式、クォート・エスケープ、コメント処理を含む堅牢な .env パーサを実装。
  - 環境変数保護機構（既存の OS 環境変数は protected として上書きしない）。
  - Settings クラスを提供し、主に以下の必須設定へアクセス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL の検証
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: raw_news を元に OpenAI（gpt-4o-mini）へセンチメント解析を行い、ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄当たりの記事数/文字数上限（既定: 10 記事、3000 文字）を実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、"results" フォーマット検査、スコアの数値検証、スコア ±1.0 でクリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ処理。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を用いず、ターゲット日ベースでウィンドウを計算。
    - 部分失敗に強い DB 書き込み（該当コードのみ DELETE → INSERT を行い、他の既存スコアを保護）。
  - regime_detector モジュール: 市場レジーム判定（bull/neutral/bear）を日次で実行する機能を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成してレジームスコアを算出。
    - マクロ記事抽出はキーワードマッチ（複数キーワードリスト）で最大 20 記事を取得。
    - LLM 呼び出しは独立実装、JSON モードで厳密な JSON レスポンスを期待し、失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - リトライ・バックオフ（最大リトライ回数、5xx の扱いなど）。

- データ処理モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - 最大探索日数制限や健全性チェック、バックフィルの考慮を実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存する夜間ジョブを実装。バックフィルや取得範囲制御を含む。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - ETL パイプラインの骨子（差分取得、保存、品質チェック）を実装するためのユーティリティ関数を提供。
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を公開エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR ベースのボラティリティ、流動性（20 日平均売買代金・出来高比率）、Value（PER, ROE）などの定量ファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials のみ参照する設計（本番口座や注文系 API にアクセスしない）。
    - データ不足時の扱い（None 戻し）や結果を (date, code) キーの dict リストで返す仕様。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman ランク相関）計算、ランク付けユーティリティ、ファクター統計サマリを実装。
    - 外部依存を避け、標準ライブラリのみで実装。

- 設計方針（横断的）
  - ルックアヘッドバイアス回避のため、関数は全て target_date ベースで動作し、現在時刻を直接参照しない。
  - OpenAI 呼び出し時は JSON Mode を利用し、レスポンスのパース失敗や API 問題はフェイルセーフ（例: 0.0 中立化・スキップ）で処理を継続する方針。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT など）。
  - DuckDB 互換性に配慮した実装（executemany の空リスト回避など）。

### 変更（Changed）
- 新規パッケージのため該当なし。

### 修正（Fixed）
- 新規パッケージのため該当なし。

### 既知の制限・注意点（Notes / Known limitations）
- OpenAI の利用には OPENAI_API_KEY（もしくは関数引数での api_key 注入）が必須。未設定時は ValueError を送出。
- .env パーサは一般的なケースをかなりカバーしますが、極端に特殊な .env フォーマットには未検証。
- news_nlp / regime_detector の LLM 呼び出しは gpt-4o-mini を前提に実装されている（モデル名は定数で管理）。
- DuckDB に依存するため、実行環境に DuckDB が必要。
- calendar_update_job 等は外部の J-Quants クライアント（kabusys.data.jquants_client）に依存しており、実運用では API クレデンシャルやネットワークアクセスが必要。
- ETL / pipeline の完全なワークフローは外部 API 実装および quality モジュールの振る舞いに依存。

### セキュリティ（Security）
- なし（初回リリース時点で既知のセキュリティ修正はなし）。

---

※ 本 CHANGELOG はリポジトリ内のソースコード（コメント、関数名、ドキュメント文字列）から実装内容を推測して作成しています。実際のリリースノートや運用ドキュメントと差異がある可能性があります。必要があれば追加の説明や細かな変更点の分割（例えば ai モジュール内の個別関数ごとの履歴）を追記します。
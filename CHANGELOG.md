# Changelog

すべての変更は "Keep a Changelog" の形式に従っています。  
このファイルではパッケージ kabusys の初期リリース（v0.1.0）で導入された主要な機能、挙動、設計上の注意点をコードベースから推測して記載しています。

なお、本リリースはソース内の __version__ = "0.1.0" に基づく初回公開相当のまとめです。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ本体
  - パッケージのエントリポイントを導入（src/kabusys/__init__.py）。主要サブパッケージとして data, research, ai, 等を公開。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化サポート（テスト用）。
  - .env パーサを実装（export 形式、クォート文字列、エスケープ、インラインコメントの扱いを考慮）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー
- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント解析 (news_nlp.py)
    - raw_news / news_symbols を集約して銘柄単位のテキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信して ai_scores テーブルへ書き込む。
    - チャンク単位（デフォルト最大 20 銘柄）でのバッチ処理、1 銘柄あたり記事数・文字数の上限を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しに対するリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score の型チェック、スコアのクリップ）。
    - 書き込みは部分失敗に備え、取得できたコードのみ DELETE → INSERT による置換。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）と、マクロニュースの LLM（重み 30%）を合成して日次で market_regime テーブルへ判定結果を書き込む。
    - マクロ判定はマクロキーワードでフィルタしたニュースタイトルを LLM（gpt-4o-mini）へ投げ、JSON 形式の {"macro_sentiment": float} を期待。
    - API 呼び出しのリトライ・フェイルセーフ実装。API 失敗時は macro_sentiment = 0.0 として継続。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。
- データ処理 / Data Platform (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar に基づく営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB のカレンダーデータがない場合は曜日ベース（土日非営業日）でフォールバックする設計。
    - calendar_update_job を実装し、J-Quants からの差分取得 → market_calendar へ冪等保存を行う（バックフィル・健全性チェックあり）。
  - ETL / パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを実装（ETL の実行結果・品質問題・エラーを集約）。
    - _get_max_date などの内部ユーティリティを実装。
    - etl モジュールは pipeline の ETLResult を再エクスポート。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの収集を採用。
  - jquants_client インターフェースを想定した fetch/save の利用（calendar_update_job などが依存）。
- リサーチ / ファクター計算 (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、
      バリュー（PER, ROE）を計算する関数群を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す挙動。
    - 全関数は prices_daily / raw_financials のみを参照（安全設計）。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンを一度のクエリで取得する実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の計算（同順位は平均ランク）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリ（factor_summary）を実装。
- logging / 設計上の注意点
  - 多くのモジュールでログ（logger）を用いた情報・警告出力を実装。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() に依存しない実装方針が明記されている（各関数で target_date を明示的に受け取る）。

### 変更 (Changed)
- （初回リリースのため該当なし。コードには多数の設計方針・制約が明記されています。）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数から必須取得となる（設定がない場合は ValueError を送出する箇所あり）。
- .env 自動読み込み時に既存 OS 環境変数を保護する仕組み（protected set）を実装。

### 既知の制限 / 注意点 (Known issues / Notes)
- OpenAI 連携は gpt-4o-mini を前提とした JSON mode を利用しているため、OpenAI SDK のバージョンやレスポンス形式の変化に影響される可能性があります。API エラーやパース失敗は多くの箇所でフェイルセーフ（0.0 やスキップ）にフォールバックする設計です。
- calc_value では PER と ROE のみ実装。PBR や配当利回りは未実装（コード中に注記あり）。
- DuckDB に対する executemany の挙動（空リスト不可など）を考慮した実装になっているため、DuckDB のバージョン差異に注意が必要です。
- 日付・時刻は基本的に naive な date / datetime を使用しており、UTC / JST の変換はモジュール内で明確に扱われています（news window 等）。
- Python の型記法（| を用いたユニオン）や from __future__ imports から Python 3.10 以上を想定している可能性が高いです。
- 外部依存: duckdb, openai（OpenAI Python SDK）, および J-Quants 用のクライアント層（kabusys.data.jquants_client）が必要。

---

開発チーム・利用者向けの補足
- 環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（主にテスト用途）。
- AI 系の処理を実行するには OPENAI_API_KEY を環境変数、または各関数の api_key 引数で指定する必要があります。
- データベーススキーマ（tables: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を事前に準備してください。各モジュールはこれらのテーブルを前提とした実装です。

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時はリリース日や変更理由、マイグレーション手順等を追記してください。）
# CHANGELOG

すべての変更点は「Keep a Changelog」準拠の形式で記載しています。  
この変更履歴は提示されたコードベースの内容から実装方針・機能を推測して作成したものであり、実際のコミット履歴ではありません。

全般:
- 日付は本ファイル生成日（2026-04-01）を基準にしています。
- バージョン番号はパッケージ内の __version__ に合わせて 0.1.0 を初版としています。

## [Unreleased]
- 今後の予定 / 改善案（コードから推測）
  - OpenAI クライアントの抽象化（テスト容易性・ベンダーロックイン緩和）。
  - monitoring パッケージの実装・監視ジョブ周りの統合（__all__ に monitoring が含まれるため実装予定と思われる）。
  - DuckDB バインドやバージョン依存の互換性チェック強化（executemany の空リスト制約等の扱いを安定化）。
  - テスト用のモックヘルパー追加（外部API 呼び出しの差し替えをさらに簡易にするユーティリティ）。
  - ドキュメント整備（API 使用例、環境変数一覧、運用手順）。

---

## [0.1.0] - 2026-04-01
初期リリース（推測）。以下の主要機能と実装方針が含まれます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring（monitoring は名前は公開されているが実装は別途存在する想定）。
  - パッケージバージョン: 0.1.0。

- 設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env と .env.local の優先度処理を実装（OS 環境変数保護、override ロジック）。
  - export KEY=val 形式、クォート／エスケープ、行内コメントのパースに対応したカスタムパーサを実装。
  - 環境変数からの設定取得をラップする Settings クラスを追加。主要な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK閾値
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG..CRITICAL）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- データ (src/kabusys/data/)
  - calendar_management.py
    - JPX（J-Quants）市場カレンダーの夜間バッチ更新処理（calendar_update_job）。
    - market_calendar テーブルに基づく営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得日の曜日ベースフォールバック、最大探索日数制限、安全性チェック、バックフィルの実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを提供（ETLの集計結果格納）。
    - ETL の差分取得・保存・品質チェックを行うパイプライン設計（jquants_client と quality モジュールを使用）。
    - ETL の設計方針（差分更新・バックフィル・部分失敗時の保護など）を反映。
  - etl は ETLResult を公開（data/etl.py から再エクスポート）。

- AI (src/kabusys/ai/)
  - news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数／文字数制限、JSON Mode のレスポンス検証、リトライ（429/ネットワーク/5xx）等を含む堅牢な実装。
    - calc_news_window 関数（対象日の前日15:00 JST〜当日08:30 JST を UTC ベースで返す）。
    - API キー注入（api_key 引数または OPENAI_API_KEY 環境変数）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）。
    - 外部依存最小化（標準ライブラリ中心、テスト用フックあり）。
  - regime_detector.py
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能を実装。
    - ma200_ratio 計算、マクロニュース抽出（マクロキーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini）、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - リトライと指数バックオフ、API エラーの区別（5xx 再試行、非5xx は即フォールバック）。
    - OpenAI 呼び出しは news_nlp と別実装で分離（モジュール結合の回避）。
  - ai パッケージは score_news と score_regime を公開（news_nlp の score_news を __init__ で公開、regime_detector の score_regime がパブリックAPI）。

- Research（src/kabusys/research/）
  - factor_research.py
    - Momentum, Value, Volatility, Liquidity 等のファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算（データ不足時の None 処理）。
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率の計算。
    - calc_value: 財務データ（EPS/ROE）と株価を用いて PER/ROE を計算。
    - 関数は DuckDB 接続を受け取り SQL を中心に高速に計算する設計。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）を LEAD を用いて一度に取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties 検出の堅牢化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
  - research パッケージは各種ファクター計算・統計ユーティリティを公開。

### 変更 (Changed)
- 設計方針（全体）
  - ルックアヘッドバイアス対策として、datetime.today()/date.today() を主要アルゴリズム内部で直接参照せず、target_date を明示的に受け取る設計が採用されている。
  - 外部 API 呼び出し失敗時はフェイルセーフで処理を継続する方針（例: LLM API の失敗で 0.0 フォールバック、部分的な ETL 失敗で他データ保護）。
  - DuckDB 固有の制約（executemany に空リスト不可等）に配慮した実装。

### 修正 (Fixed)
- エッジケースや耐障害性の作り込み
  - .env パーサはクォート内エスケープやインラインコメント、export プレフィックスに対応。
  - OpenAI レスポンスの JSON パース失敗時に前後テキストを含む場合の復元ロジックを導入（最外の {} を抽出）。
  - DB 書き込み失敗時に明示的に ROLLBACK を試み、ROLLBACK 自体の失敗をログ出力して上位へ例外を伝播。
  - calendar_update_job に健全性チェック（将来日に対する異常検出）およびバックフィルロジックを追加。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API
  - gpt-4o-mini（JSON Mode）を想定しているため、実運用では API 仕様・コストの検討とレート制御が必要。
  - API キーは api_key 引数または OPENAI_API_KEY 環境変数で指定。未設定時は ValueError を送出する。
  - レスポンス検証は厳格だが完全ではないため、LLM の挙動による部分的失敗はあり得る（その場合は該当チャンクをスキップ）。
- DuckDB
  - 実装は DuckDB を前提としており、一部バインド挙動がバージョン依存（executemany の空リスト等）。
- 時刻/タイムゾーン
  - raw_news.datetime は UTC で保存されている前提。calc_news_window は JST を基準に計算して UTC naive datetime を返す。
- テスト用フック
  - _call_openai_api 等はテスト時にモック差し替えを想定している（unittest.mock.patch の利用を想定）。
- 部分的に未完成箇所
  - src/kabusys/data/pipeline.py の末尾が不完全に見える箇所があり（コード切れの可能性）、実際の実装では細かい補完が必要。

### セキュリティ (Security)
- 環境変数の扱い
  - OS 環境変数を保護する protected キーセットが導入されており、自動 .env ロード時の上書きを制御。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

署名:
- この CHANGELOG は提示されたソースコードの構造・ドキュメント文字列から推測して作成したものです。実際のコミット・変更履歴を反映するためには、git の履歴やリリースノートを基に更新してください。
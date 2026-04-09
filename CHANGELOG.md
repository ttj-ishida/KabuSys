# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（src/kabusys/*）の内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回公開リリース。以下の主要機能・モジュールを実装・公開。

### Added
- パッケージのバージョン情報を追加
  - kabusys.__version__ = "0.1.0"

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数の自動読込機能を実装（プロジェクトルート検出: .git または pyproject.toml を参照）。
  - .env/.env.local の読み込み順序・上書き制御（OS 環境変数保護機構あり）。
  - export 形式やクォート・インラインコメントのパース対応。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
  - 各種設定プロパティ（J-Quants トークン、kabu API、LINE トークン、DBパス、Paper Trading 設定、監視閾値、環境モード判定など）。
  - 環境値の妥当性検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証と例外処理）。

- データ層（kabusys.data）
  - calendar_management:
    - JPX カレンダーを扱うユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar の有無に応じた曜日ベースのフォールバック実装。
    - calendar_update_job: J-Quants から差分取得して idempotent に保存する夜間バッチ処理（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETL パイプラインのインターフェースと ETLResult データクラスを追加（取得数・保存数・品質問題・エラー一覧を保持）。
    - デフォルトのバックフィルや calendar lookahead 設定による差分更新方針を実装。
  - jquants_client / quality など外部クライアントとの連携を想定した設計（実装ファイルは別モジュール参照として組み込み）。

- ニュース NLP / AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出。
    - calc_news_window による JST 時間窓計算（前日 15:00 JST ～ 当日 08:30 JST の変換ロジック）。
    - _score_chunk / _validate_and_extract によるチャンク処理、応答バリデーション、スコアクリッピング（±1.0）、最大記事数・文字数トリム、バッチ処理（最大 20 銘柄/コール）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ、フェイルセーフで失敗銘柄をスキップ。
    - score_news(conn, target_date, api_key=None): ai_scores テーブルへ置換保存（部分失敗時に既存スコアを保護するため code を絞って DELETE → INSERT）。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini、JSON 出力期待）。記事なしの場合は LLM 呼び出しをスキップして macro_sentiment=0 を採用。
    - API 呼び出しのリトライ、エラー時のフォールバック（macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、ROLLBACK の保護ログ。
    - score_regime(conn, target_date, api_key=None) を提供。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）などのモメンタムファクター。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などのボラティリティ・流動性ファクター。
    - calc_value: raw_financials から EPS/ROE を組合せて PER/ROE を計算（最新の報告日までを参照）。
    - DuckDB を利用した SQL ベースの実装、データ不足時の None 処理、入力表は prices_daily / raw_financials 限定。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（horizons デフォルト [1,5,21]、horizons のバリデーション）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・None 除外・最小有効レコード数チェック）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 判定対策）。
    - factor_summary: カウント・平均・標準偏差・最小/最大/中央値の統計サマリー。

- 公開 API の整理
  - 各サブパッケージの __init__.py で主要関数を再エクスポート（例: kabusys.ai.score_news / kabusys.ai.score_regime / kabusys.research.* / kabusys.data.ETLResult 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の安全対策）。
- OS の既存環境変数はデフォルトで上書きされない設計（protected set による保護）。

### Notes / 設計上の考慮点
- ルックアヘッドバイアス防止: 全ての AI / 指標計算は datetime.today() / date.today() を直接参照せず、呼び出し元が target_date を指定する設計。
- フェイルセーフ: LLM API の失敗は致命的エラーとせず、フェールオーバー（0.0 スコア）やスキップ処理を行うことで処理継続を優先。
- DuckDB 互換性: executemany に対する空パラメータ回避など、DuckDB バージョン依存の注意点をコード内で扱っている。
- トランザクション安全性: DB 書込みは BEGIN / COMMIT / ROLLBACK を明示的に扱い、ROLLBACK の失敗をログに残す実装。
- OpenAI SDK 依存: gpt-4o-mini を想定した実装。API 呼び出し箇所はテスト容易性のため差し替え可能（内部関数を patch する設計）。

### Dependencies（想定）
- duckdb
- openai（OpenAI Python SDK）
- Python 3.10+（型ヒントに union 型 | を使用）

### Breaking Changes
- 初回リリースのため該当なし

---

（注）本 CHANGELOG は提供されたソースコードの内容から機能と設計意図を推測して作成しています。実際のリリース日や外部モジュールの実装状況に応じて適宜調整してください。
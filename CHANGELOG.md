# Changelog

すべての重要な変更を記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-26

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env を上書き（ただし OS 環境変数は保護される）。
  - 強力な .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理などに対応。
  - 必須設定チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等をプロパティ経由で取得し、未設定時は ValueError を発生させる。
  - 設定検証: KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 値の検証メソッドを実装。
  - デフォルトの DB パス（duckdb, sqlite）を Path として返す。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から対象時間ウィンドウの記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0～1.0）を取得。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（1リクエスト最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限でトークン膨張を抑制。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ（リトライ）を実装。その他エラーはスキップし継続するフェイルセーフ設計。
    - OpenAI レスポンスの厳密なバリデーションと復元処理を実装（JSON パース失敗時に最外側の {} 抽出等）。
    - スコアは ±1.0 にクリップ。取得済みコードのみを ai_scores テーブルに対して DELETE → INSERT で置換（部分失敗時に既存データ保護）。
    - テスト用に _call_openai_api を patch しやすい構造。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window と raw_news から抽出、OpenAI（gpt-4o-mini）でセンチメント（-1.0～1.0）を取得し、再試行・フォールバック（API 失敗時は macro_sentiment=0.0）を備える。
    - スコア合成後は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替えやすく設計。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム / ETL（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）データを扱うユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB の登録値を優先し、未登録日は曜日ベース（週末は非営業日）でフォールバックする一貫した挙動。
    - 最大探索範囲や健全性チェック（最大未来日数等）を実装して無限ループや異常データを防止。
    - calendar_update_job により J-Quants API から差分取得 → jq.save_market_calendar に保存（バックフィル、サニティチェック、エラーハンドリングを含む）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー一覧などを格納）。
    - 差分取得・backfill・データ保存・品質チェックのためのユーティリティ関数を実装（_get_max_date, _table_exists など）。
    - データ品質チェックモジュール（kabusys.data.quality への依存）は ETLResult に収集して、呼び出し元での判定を想定（Fail-Fast ではない）。
    - etl モジュールは ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M）、200 日移動平均乖離、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算する関数を追加。
    - 入力データ不足時の挙動（該当値を None）や、返却形式は date/code を含む dict リスト。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応、ホライズン検証/範囲制限あり。
    - IC（Information Coefficient）計算（calc_ic）：ファクター値と将来リターンのスピアマンランク相関を計算。十分なサンプルがない場合は None を返す。
    - rank ユーティリティ：同順位は平均ランク、丸め処理により浮動小数点の ties 問題を回避。
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリ関数。
  - research パッケージの __init__ で主要関数を再公開（calc_momentum 等）。

### Design / Reliability
- ルックアヘッドバイアス防止:
  - news_nlp, regime_detector, research の各モジュールは datetime.today()/date.today() を内部で直接参照しない設計（外部から target_date を注入）。
  - DB クエリは target_date 未満/未満等の排他条件を取り入れ、将来データ参照を回避。
- フェイルセーフ思想:
  - AI 呼び出し失敗時はスコアを 0.0 にフォールバック（regime_detector）や該当チャンクをスキップ（news_nlp）するなど、ETL/解析処理を継続可能にする設計。
- DuckDB 互換性考慮:
  - executemany に空リストを渡せない DuckDB 0.10 の挙動を考慮して空チェックを実施。
- ロギングと詳細な警告/情報ログを各モジュールに追加（失敗時の原因追跡を容易に）。

### Notes / Requirements
- OpenAI API 連携:
  - gpt-4o-mini を想定、OpenAI Python SDK の例外（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）をハンドリング。
  - API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。
- J-Quants クライアント（kabusys.data.jquants_client）に依存する実装箇所あり（calendar_update_job 等）。
- テストしやすさを考慮して各所で _call_openai_api の差し替えや API キー注入、DB 接続注入をサポート。

---

今後のリリースでは以下のような拡張を想定しています（例）:
- strategy / execution / monitoring モジュールの実装強化（実売買連携、バックテスト等）
- ai モデルのオプション化やローカルモデル対応
- より詳細なデータ品質チェックおよび可観測性（メトリクス、トレース）の追加

（注）本 CHANGELOG はコードベースから推測して作成しています。機能仕様や設計意図はソースコメント・ docstring に基づく推定です。必要に応じて実際の変更履歴・リリースノートに合わせて調整してください。
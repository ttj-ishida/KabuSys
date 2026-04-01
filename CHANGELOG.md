CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

なお、この CHANGELOG は提供されたコードベースの内容から実装意図を推測して作成しています。

Unreleased
----------

- （今後のリリースに記載）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期化
  - パッケージ版 (kabusys) の初期バージョンを追加。
  - __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / config
  - .env ファイルや環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。
  - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定時のみセット）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export 形式、クォート、エスケープ、コメント（ハッシュ）の取り扱いに対応。
  - 必須環境変数取得時の検査（_require）と、KABUSYS_ENV / LOG_LEVEL のバリデーション。
  - デフォルト設定値: KABUSYS 用 DBパス（DUCKDB_PATH / SQLITE_PATH）、監視設定（PID ファイル、閾値）など。

- データ層 (kabusys.data)
  - market_calendar 管理と営業日判定ロジックを実装（calendar_management）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルが未整備でも曜日ベースのフォールバックを採用（週末は非営業日）。
    - DB 登録データ優先・未登録日は曜日フォールバックの一貫性を保持。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・冪等保存ロジックを実装。
  - ETL パイプライン関連のインターフェースを追加（pipeline.ETLResult を公開）。
  - pipeline モジュール（ETLResult, 内部ユーティリティ）
    - ETLResult データクラスを導入（取得件数・保存件数・品質チェック結果・エラー一覧などを保持）。
    - ETL 実装方針（差分取得、バックフィル、品質チェックの扱い）を反映する設計。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを追加。

- J-Quants クライアント連携（コード参照箇所）
  - data モジュールは jquants_client を利用してカレンダー / データの取得・保存を行う想定。

- リサーチ / research
  - factor_research モジュール（ファクター計算）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - 各関数は DuckDB への SQL クエリで実装され、欠損やデータ不足時の挙動（None 戻り）を明確化。
  - feature_exploration モジュール（特徴量探索）
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21 営業日）の将来リターン計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None。
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 実装は外部依存（pandas 等）なしで標準ライブラリ + DuckDB で完結する設計。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール（ニュースセンチメント）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄／API コール）、1 銘柄あたりの記事数・文字数トリム（上限: 10 記事、3000 文字）。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスのバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装（最大リトライ回数・待機時間は定数で制御）。
    - エラーやパース失敗は例外を投げず該当チャンクをスキップするフェイルセーフ設計。
    - テスト容易性: _call_openai_api を patch してモック可能。
    - ニュース時間ウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（UTC に変換して DB クエリで比較）。
  - regime_detector モジュール（市場レジーム判定）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を決定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（複数キーワードリストあり）。
    - LLM には gpt-4o-mini を使用、JSON レスポンスを期待。API 失敗時は macro_sentiment = 0.0 のフォールバック。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値で bull / bear / neutral を判定（閾値 0.2）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を行い例外を再送出。
    - lookahead バイアス回避のため target_date 未満のデータのみ参照、date.today() 参照を避ける設計。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Notes / Implementation & Usage details
- OpenAI API 鍵
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数を受け付ける。None の場合は環境変数 OPENAI_API_KEY を参照。
  - API キーが設定されていない場合は ValueError を送出するため、呼び出し側で確実な設定が必要。
- フェイルセーフ設計
  - AI 呼び出しや外部 API エラー時は可能な限り処理を継続し、局所的な結果欠如（スコア欠落）に留める設計。
  - DuckDB への書き込みは冪等（既存行を削除してから挿入）を意図して実装。
- テスト容易性
  - OpenAI 呼び出し箇所はモック差し替えが想定されており、単体テストで外部 API を叩かずに検証可能。
- 時刻 / タイムゾーン
  - ニュース集計ウィンドウ等は JST を起点に UTC naive datetime で DB と比較する（timezone 混入を避ける）。
- 外部依存
  - DuckDB を主要な計算・保持層として利用。外部ライブラリ（pandas 等）に依存しない実装方針。

Security
- （初版のため該当なし）

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成されています。実際のリリースノートや変更履歴はリポジトリのコミットログやリリースプロセスに基づいて更新してください。
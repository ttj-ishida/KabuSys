# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠しています。  

※リリース日: 2026-03-28

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- 基本パッケージ
  - パッケージ初期化: kabusys パッケージを導入。__version__ = "0.1.0"、公開モジュール一覧を __all__ で定義。
- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索して決定（CWD非依存）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを独自実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
  - 環境変数の保護（protected set）を考慮した読み込み／上書き制御。
  - Settings クラスを提供（J-Quants、kabuステーション、Slack、DBパス、実行環境、ログレベル等のプロパティを公開）。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値のチェック、未設定時のエラー／デフォルト値）。
  - 必須値未設定時は _require により明示的な ValueError を送出。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数上限、JSON Mode 専用のレスポンス検証・パース処理を実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。非リトライ対象のエラーはスキップして処理継続（フェイルセーフ）。
    - レスポンスのバリデーション機能（results 配列・code/score の存在と型チェック・未知コード無視・スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは部分更新（対象コードのみ DELETE → INSERT）で冪等性と部分失敗時の既存データ保護を確保。
    - テスト容易性のため内部の API 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定・保存。
    - ma200_ratio の計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 算出、両者を合成して regime_label（bull/neutral/bear）を決定。
    - API 呼び出し失敗時は macro_sentiment = 0.0 でフォールバック（フェイルセーフ）。JSON パース・API エラー時のリトライロジックを実装。
    - DB 書込はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に処理。失敗時は ROLLBACK を試行し、問題があればログ出力。
- データ管理（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダーデータ未取得時は曜日ベース（土日を休日）でフォールバックする一貫した挙動を提供。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に保存。バックフィル日数、先読み、健全性チェックを実装。
    - 検索範囲の上限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧などを集約）。
    - 差分取得、保存、品質チェックの設計方針を実装（backfill、idempotent 保存、品質チェックは収集して呼び出し元に委ねる）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - ETL 再公開（etl.py）: pipeline.ETLResult を再エクスポート。
  - jquants_client / quality 等へのインタフェースを想定した実装。
- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（価格・財務データからモメンタム、ATR、出来高/売買代金、PER/ROE 等を計算）。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary を実装（将来リターン、スピアマンIC、ランク付け、統計サマリ）。
  - すべて DuckDB と標準ライブラリのみで実装（外部依存を最小化）。
- テストしやすさ
  - OpenAI 呼び出しや内部処理の差し替えポイントを用意し、ユニットテストでのモック化を容易化。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardening
- DuckDB 特有の挙動（executemany に空リストが渡せない等）を考慮した安全な executemany 呼び出し実装。
- トランザクション失敗時に ROLLBACK を試行し、ROLLBACK 自体の失敗もログに記録するように実装。
- 外部 API 呼び出し周りで「5xx はリトライ、それ以外は即スキップ」「リトライ回数制限」「指数バックオフ」など堅牢化。
- ルックアヘッドバイアス防止: 処理は内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る API）。

### Security
- 外部 API キー（OpenAI）の取り扱いは引数注入または環境変数（OPENAI_API_KEY）で明示的に管理。未設定時は ValueError を送出して安全に停止。

### Breaking Changes
- なし（初回リリース）

---

開発者向け補足（実装上の重要ポイント）
- 環境変数ロードはプロジェクトルート検出に依存するため、パッケージ配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- AI モジュールは JSON Mode（OpenAI の response_format）を前提に厳密な JSON パースと検証を行うため、モデル出力のフォーマット逸脱に対してフォールバック・ログ出力を行います。
- DuckDB への書き込みは「対象を絞った削除 → 挿入」という手順を採り、部分失敗時に既存の他コードのスコアを消さないように配慮しています。

（以上）
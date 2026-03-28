CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-28
--------------------

初期リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加機能と設計上の方針は以下の通りです。

Added
- パッケージ基盤
  - kabusys.__version__ を "0.1.0" として定義。
  - パッケージの公開 API を __all__ で指定（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定アクセスを統一。必須変数取得時に未設定なら ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。

- AI 関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数上限、JSON Mode を利用した頑健な応答検証を実装。
    - API の429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ、部分成功時に他銘柄スコアを保護するための部分置換(DELETE→INSERT)戦略を採用。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - calc_news_window: JSTベースのニュース収集ウィンドウ計算（前日15:00～当日08:30 JST を UTC に変換して扱う）。
  - regime_detector モジュール
    - 日次での市場レジーム判定を実装。ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を判定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足は中立値1.0にフォールバック）。
    - マクロニュース抽出（キーワードベース）と OpenAI 呼び出し、リトライとフォールバック（API失敗時 macro_sentiment=0.0）。
    - レジームスコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、平均売買代金・出来高変化率など、複数の定量ファクター計算を実装。DuckDB の SQL ウィンドウ関数を活用。
    - データ不足時には None を返すなど安全な扱い。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（任意ホライズン、範囲チェック）、IC（スピアマンランク相関）calc_ic、ランク変換 rank、factor_summary（統計サマリー）などを実装。
    - pandas 等の外部依存を使わず、標準ライブラリのみで実装。
  - research パッケージ __all__ に主要関数を公開。

- データ基盤（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）用ユーティリティ。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 未取得時は曜日ベースのフォールバックを行い、DB 登録値は優先して使用する一貫性のある判定ロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存処理）。
  - pipeline モジュール
    - ETL パイプライン用ユーティリティ。差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュールと連携）フローを設計。
    - ETLResult dataclass を実装（取得件数/保存件数/品質問題/エラーメッセージ等を格納）。to_dict によるシリアライズを提供。
  - etl モジュールで ETLResult を再エクスポート。

- 汎用 / 実装方針（全体）
  - DuckDB を第一級サポート（すべての計算・クエリは DuckDB 接続を受け取る設計）。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を処理内部で直接参照せず、外部から target_date を受け取る方針を徹底。
  - DB 書き込みは可能な限り冪等（削除→挿入や ON CONFLICT を想定）に実装。
  - 失敗時はフェイルセーフ（例: API 失敗で0.0フォールバック、部分失敗で他データ保護）を採用。
  - ロギング（情報、警告、例外の記録）を広範に実装し運用観測を容易に。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Notes / 補足
- OpenAI の呼び出しは openai.OpenAI クライアントを利用する想定。API キーは関数引数で注入可能（テスト時は環境変数 OPENAI_API_KEY か引数で指定）。
- .env の自動読み込みでは OS 環境変数を保護する仕組みを実装（.env.local の override 時でも OS の既存変数は上書きしない）。
- DuckDB の executemany に関する互換性（空リスト不可）に配慮した実装を行っている。

今後
- strategy / execution / monitoring パッケージの実装・連携、より詳細な品質チェックモジュールや運用向け監視・アラート機能の追加を予定。
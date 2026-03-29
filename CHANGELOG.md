CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

0.1.0 - 2026-03-29
------------------

Added
- 基本パッケージ初期リリース（kabusys v0.1.0）。
- パッケージ構成:
  - kabusys.config: 環境変数/設定管理
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
    - .env パーサ改善: export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱いの制御。
    - OS 環境変数を保護するため protected セットを導入し、.env.local での上書き動作を制御。
    - 必須環境変数取得時に未設定なら ValueError を投げる _require() ユーティリティ。
    - 各種設定プロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト), SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH の既定パス
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev の便利プロパティ
  - kabusys.ai:
    - news_nlp.score_news:
      - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書込む。
      - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
      - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリム。
      - JSON Mode を利用したレスポンス検証と厳格なバリデーション（results 配列、コードの照合、数値検証）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - スコアは ±1.0 にクリップ。部分失敗に備えて書込前に該当コードのみ DELETE → INSERT（冪等性・部分失敗耐性）。
      - テスト容易性のため _call_openai_api の差し替え（unittest.mock.patch）を想定。
    - regime_detector.score_regime:
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルに書き込む。
      - MA200 乖離はルックアヘッドを防ぐため target_date 未満のデータのみで計算し、データ不足時は中立値（1.0）を使用。
      - マクロニュースは predefined キーワードでフィルタし、LLM（gpt-4o-mini）に投げて -1.0～1.0 に正規化した macro_sentiment を取得。API 失敗時は 0.0 にフォールバック（フェイルセーフ）。
      - レジームスコアをクリップし、閾値に応じて "bull"/"neutral"/"bear" を判定。DB に対して冪等な BEGIN/DELETE/INSERT/COMMIT を実行。
      - OpenAI 呼び出しも個別実装し、モジュール結合を避ける設計。
  - kabusys.research:
    - factor_research:
      - calc_momentum: 1M/3M/6M のモメンタム、200 日移動平均乖離を計算（データ不足は None）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足は None）。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損なら None）。PBR・配当利回りは未実装。
    - feature_exploration:
      - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の妥当性チェックあり（1..252）。
      - calc_ic: スピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None を返す。
      - rank: 同順位は平均ランクで処理（浮動小数の丸め対策あり）。
      - factor_summary: count/mean/std/min/max/median を計算。
    - kabusys.data.stats の zscore_normalize を再エクスポート。
  - kabusys.data:
    - calendar_management:
      - market_calendar を利用した営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末判定）。最大探索日数制限で無限ループを防止。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を更新。バックフィルと健全性チェックを実装。
    - pipeline / etl:
      - ETLResult データクラスの追加（ETL の取得・保存数、quality_issues、errors を格納）。
      - 差分更新・バックフィル・品質チェック（quality モジュール連携）など ETL ワークフローの骨格を実装。
      - jquants_client と quality の呼び出しに対する例外処理とロギングを実装。
    - etl.py で ETLResult を公開再エクスポート。
  - モジュール初期化:
    - 各パッケージで __all__ を定義し、公開 API を整理（kabusys, kabusys.ai, kabusys.research など）。

Changed
- n/a（初期リリースのため変更履歴はなし）。

Fixed
- n/a（初期リリースで既知バグ修正はなし）。

Deprecated
- n/a

Removed
- n/a

Security
- 環境変数の取り扱いを厳格化:
  - 必須値の未設定は明確なエラーを出すことで秘密情報の未設定に早期に気づけるようにした。
  - .env の読み込み時に OS 環境変数を保護（.env.local でも明示的には上書き可能だが、初期ロードで OS 環境を保護する仕組みを導入）。

Notes / 実装上の注意
- 全てのモジュールはルックアヘッドバイアスを避けるため、date.today() / datetime.today() に依存しない設計方針を明示的に採用。
- OpenAI 呼び出し箇所はテスト容易性のため差し替え可能な形で実装（private 関数の patch を想定）。
- DuckDB に対する executemany の空リストバインドに対する対策（空時は呼ばない）を実装。
- 一部処理は外部 API（J-Quants / OpenAI）に依存するため、API エラー時はフォールバックやスキップ、ログ出力で安全に継続する方針。

Contributing
- バグ報告・機能提案は issue を作成してください。プルリクエストの際はユニットテストと簡単な説明を添えてください。
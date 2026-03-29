KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットに準拠: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- なし

0.1.0 - 2026-03-29
------------------
Added
- パッケージ基盤
  - パッケージバージョンを公開: kabusys.__version__ = "0.1.0"
  - パッケージ公開 API を定義: kabusys は data, strategy, execution, monitoring を __all__ で公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 自動読み込みの優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用フック）。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env の柔軟なパース実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（条件付き）に対応。
    - 無効行のスキップ、読み込み失敗時は警告ログ。
    - override / protected オプションにより OS 環境変数を保護して上書き制御。
  - Settings クラスを提供し、アプリで使用する主要設定をプロパティで公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development / paper_trading / live 検証）と LOG_LEVEL 検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は ValueError を発生させる _require() を採用（誤設定を早期検出）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）に送信しセンチメント（-1.0〜1.0）を算出。
    - 処理ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）。
    - バッチ処理: 最大 20 銘柄/回、1 銘柄あたり最大 10 記事、3000 文字までトリム。
    - JSON Mode を使用しレスポンスを厳密に検証。部分的に不正なレスポンスは無視して他銘柄は保持する設計。
    - リトライ／バックオフ: 429（レート制限）・ネットワーク断・タイムアウト・5xx に対して指数バックオフで再試行。
    - API 呼出し箇所はテスト差替え用に _call_openai_api を局所実装（モジュール間依存を避ける）。
    - スコアは ±1.0 にクリップし、取得成功銘柄のみを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - 空結果や致命的な失敗はログに記録してフェイルセーフ（処理継続）を採用。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はタイトルベースでマクロキーワード群を検索（最大 20 件）。
    - OpenAI 呼び出しは gpt-4o-mini を使用、JSON レスポンスをパースして macro_sentiment（-1〜1）を取得。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバックして例外を伝播。
    - API 呼出しの再試行、指数バックオフ、HTTP 5xx 判定など堅牢性を考慮。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定や SQ 日判定を提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - market_calendar 未取得時は曜日ベース（平日）でフォールバックする一貫したロジックを採用。
    - カレンダー夜間バッチ更新 job を実装（calendar_update_job）。J-Quants から差分取得し冪等保存。バックフィルと健全性チェックを実装。
    - 最大探索日数の上限を設け無限ループを回避（_MAX_SEARCH_DAYS）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入し ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を整理して返却可能に。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client 経由で idempotent に保存）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデイ調整など。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離率）
    - Volatility & Liquidity: atr_20（20日 ATR）・atr_pct・avg_turnover・volume_ratio
    - Value: per（price/EPS）・roe（最新財務データを用いて target_date 以前の最新財務レコードを参照）
    - DuckDB のウィンドウ関数を活用して営業日ベースの計算を行い、データ不足は None を返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon の LEAD を使い一括取得、horizons の引数検証あり。
    - IC 計算（calc_ic）: スピアマンのランク相関（ランクは ties を平均ランクで処理）を実装。有効レコードが 3 未満なら None。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリ + duckdb で完結する実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし（ただし OpenAI/J-Quants の API キーを環境変数で管理することを前提。Settings で必須キーがない場合は例外を出すことで誤設定を検出）

マイグレーション / 利用開始メモ
- 必須環境変数:
  - OPENAI_API_KEY (news_nlp / regime_detector の API 呼び出しに必要)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベースパスはデフォルトで data/kabusys.duckdb（DUCKDB_PATH）と data/monitoring.db（SQLITE_PATH）を使用。必要に応じて環境変数で上書き。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化可能。
- OpenAI 呼び出し部分はユニットテストで _call_openai_api を patch して差し替えることを想定（モジュール内で差替えられる設計）。

既知の設計上の注意点
- ルックアヘッドバイアス防止のため、全てのモジュールで datetime.today() / date.today() を直接参照せず、target_date 引数ベースで処理を行う設計になっている。
- AI レスポンスの不確実性に対しては「スキップして継続」「フェイルセーフ（デフォルト値を使用）」のポリシーを採用しており、部分失敗時に既存データを保護するために書き込み対象を絞って置換している。
- DuckDB の executemany の挙動（空配列不可）を考慮して空チェックを行っている。

連絡・貢献
- バグ報告や提案は issue を作成してください。初期リリースのため API 仕様変更や安定化作業が今後行われる可能性があります。
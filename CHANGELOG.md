CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に準拠しています。

フォーマット
------------
- 期間: リリースごとに日付を記載
- セクション: Added / Changed / Fixed / Security / Notes

0.1.0 - 2026-03-28
------------------

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能群を実装しました。
主要な追加点、設計上の方針、外部依存・環境変数等は以下の通りです。

Added
-----
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定 / ロード
  - .env / .env.local /OS 環境変数から設定を読み込む自動ロード機能を実装（kabusys.config）。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存しない実装。
  - .env パーサーは以下の要素をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ）
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを公開（J-Quants / kabu API / Slack / DB パス / 環境モード /ログレベル 等のプロパティを提供）。
  - 必須環境変数未設定時は ValueError を発生させる _require() を実装。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp:
    - raw_news をバッチで OpenAI（gpt-4o-mini）に投げて銘柄ごとのセンチメント ai_score を計算し ai_scores テーブルへ保存する score_news を実装。
    - ニュース収集ウィンドウ計算 (calc_news_window)、記事集約 (_fetch_articles)、チャンク化・API 呼び出し、レスポンス検証（_validate_and_extract）を実装。
    - バッチサイズ・文字数上限、リトライ（429/ネットワーク/タイムアウト/5xx）など堅牢な実装。
    - JSON mode のレスポンスの前後ノイズへの耐性（外側の {} を抽出して復元）を実装。
    - テストしやすいように内部の API 呼び出し関数をパッチ可能に設計。
  - kabusys.ai.regime_detector:
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）判定を行う score_regime を実装。
    - ma200 計算（_calc_ma200_ratio）、マクロ記事抽出（_fetch_macro_news）、OpenAI でのセンチメントスコア化（_score_macro）を実装。
    - API の再試行/指数バックオフ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 判定結果を market_regime テーブルへ冪等に書き込むトランザクション処理を実装（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI クライアントは明示的に引数/環境変数から解決。

- Data（データ基盤）モジュール
  - calendar_management:
    - JPX カレンダー管理ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar の未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job を実装：J-Quants から差分取得 → 保存（fetch/save の呼び出し、バックフィルと健全性チェックを含む）。
  - pipeline / ETL:
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題リスト、エラーメッセージ、has_errors 等のユーティリティ）。
    - ETL ヘルパー関数（_table_exists / _get_max_date / 市場カレンダー調整など）を実装。
    - etl.py で ETLResult を再エクスポート。

- Research（研究用）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算。
    - calc_volatility: 20日 ATR, ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER / ROE を計算。
    - 実装は DuckDB SQL を主体とし、外部 API にアクセスしない安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターン計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランク化と基本統計量集計ユーティリティを提供。
  - data.stats の zscore_normalize を re-export（import 経路を公開）。

- 設計／運用上の重要点（Added）
  - ルックアヘッドバイアス防止: どのモジュールも datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - データベース書き込みは冪等性を重視（DELETE→INSERT 等、トランザクション制御）。
  - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するプロンプト設計。
  - テスト容易性: 内部 API 呼び出し関数を patch しやすく設計（ユニットテストで差し替え可能）。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- （初回リリースのため該当なし）
- 注意: OpenAI / J-Quants / Slack API キー等は必ず環境変数で管理し、レポジトリ等にコミットしないこと。

Notes / Migration / Usage
--------------------------
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
- DB パスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロード順序:
  - OS 環境 > .env.local > .env
  - テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI モデル:
  - デフォルトで gpt-4o-mini を使用（プロンプトは厳密な JSON 出力を要求）。
- フェイルセーフ:
  - AI API のエラー時は該当スコアを 0 にフォールバックする等、ETL/解析処理が全体として停止しない設計。
- テスト支援ポイント:
  - 内部の _call_openai_api 等を unittest.mock.patch で差し替え可能（テストで実 API を叩かずに検証可能）。

Authors
-------
- 初期実装チーム（コードベースから推測）

ライセンス
---------
- ソースコードにライセンスヘッダがないため、利用前にリポジトリの LICENSE を確認してください。

今後の予定（例）
-----------------
- strategy / execution / monitoring の具体的なトレード実装と統合テスト
- モデル（LLM）出力の堅牢性向上（より細かなフォールバック・再試行ポリシー）
- 追加の品質チェックルールとアラート連携（Slack 通知等）
- ドキュメント（API 利用方法、DB スキーマ、運用手順）の整備

--- 

（注）本 CHANGELOG は提示されたソースコードの内容から機能・設計方針を推測して作成しています。実際のリポジトリ履歴やコミットメッセージに基づく変更履歴とは異なる場合があります。
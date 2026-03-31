CHANGELOG
=========

すべての重要な変更履歴をここに記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ別に整理（Added, Changed, Deprecated, Removed, Fixed, Security）
- 各リリースはバージョンと日付を付与

[0.1.0] - 2026-03-31
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能を実装。
- パッケージ公開:
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - エクスポート: data, strategy, execution, monitoring（kabusys.__all__）
- 設定管理 (kabusys.config):
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは export 文、シングル/ダブルクォートのエスケープ、行末コメントの取り扱い等に対応。
  - Settings クラスで主要環境変数をラップ（必須変数取得時は未設定で ValueError を送出）。
  - 既定値: KABUSYS_ENV は development、KABUSYS_LOG_LEVEL/LOG_LEVEL の検証、デフォルト DB パス（duckdb/sqlite）、監視閾値等。
- AI モジュール (kabusys.ai):
  - news_nlp.score_news:
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数と文字数上限でトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ、レスポンスの厳密なバリデーション。
    - API 失敗時は該当チャンクをスキップし、処理は継続（フェイルセーフ）。
    - ニュースウィンドウ: target_date の「前日 15:00 JST ～ 当日 08:30 JST」を UTC に変換して処理（ルックアヘッドバイアス対策）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースで得たマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - OpenAI 呼び出しは専用実装。API 失敗時は macro_sentiment=0.0 で継続。
    - DB へは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で保存、失敗時は ROLLBACK。
    - 設計上、datetime.today() 等の参照を排し、ルックアヘッドを防止。
- Data モジュール (kabusys.data):
  - calendar_management:
    - JPX カレンダー管理、market_calendar テーブルを参照して営業日判定/翌前営業日取得/期間内営業日列挙等を提供。
    - カレンダー未取得箇所は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスで ETL の結果を構造化（取得件数・保存件数・品質問題・エラー）。
    - 差分更新、backfill、品質チェック（quality モジュール連携）設計を反映。
- Research モジュール (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを prices_daily から計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出（PBR 等は未実装）。
    - 設計方針として prices_daily/raw_financials のみ参照、実取引 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を計算。ホライズンは 1〜252 営業日制約。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3）時は None。
    - rank, factor_summary: ランク付け、基本統計量（count/mean/std/min/max/median）算出。
    - 外部依存を持たない標準ライブラリベースの実装。
- DB / トランザクション設計:
  - DuckDB を主要な解析 DB として使用。多くの関数は DuckDBPyConnection を引数に取る。
  - DB 書き込みは冪等化（DELETE→INSERT 等）して部分失敗時の既存データ保護を実施。
- ロギング / エラー処理:
  - 各モジュールで詳細な logger を使用し、失敗は警告/情報ログで扱う（致命的エラー時は例外を伝播）。
  - OpenAI 呼び出しはレスポンスパース失敗や API エラーを安全に扱う（fallback スコア、空辞書返却など）。

Fixed
- 該当なし（初回リリース）。

Changed
- 該当なし（初回リリース）。

Deprecated
- 該当なし（初回リリース）。

Removed
- 該当なし（初回リリース）。

Security
- 重要な環境変数（OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）は Settings 経由で必須チェックを行い、未設定時は ValueError を送出して明示的に扱う設計。

マイグレーション / 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API を利用する機能（score_news, score_regime）は OPENAI_API_KEY を環境変数か関数引数で指定する必要あり。
- .env の自動読み込み:
  - プロジェクトルートが .git または pyproject.toml で検出されない場合は自動ロードをスキップ。
  - OS 環境変数はデフォルトで保護され、.env の値で上書きされない（ただし .env.local は override=True のため上書き可能）。
- DuckDB / DB スキーマ:
  - 各機能は所定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在することを前提とする。初回利用前にスキーマ整備が必要。
- ルックアヘッド防止:
  - score_news / score_regime 等は内部で現在日時を直接参照せず、target_date を明示的に渡す設計。運用時は target_date を正しく指定すること。

将来の改善候補（実装方針のメモ）
- news_nlp と regime_detector における OpenAI 呼び出しの共通化（現在は意図的に別実装で分離）。
- ai スコアの追加検証や異常値処理の強化、PBR 等バリューファクターの追加実装。
- calendar_update_job の監査ログ / ジョブ実行履歴の格納。

謝辞
- 初期実装に含まれる各モジュールは、ルックアヘッドバイアス防止、冪等性重視、外部 API の堅牢性（リトライ/フォールバック）を意識して設計されています。運用・拡張にあたっては上記の設計方針を維持してください。
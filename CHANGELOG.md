# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

※ 本 CHANGELOG はソースコード（src/kabusys 以下）の内容から機能群・設計方針を推測して作成しています。実際のコミット履歴ではなく、コードベースの初期実装内容をまとめたものです。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-31

初期リリース。以下の主要機能と実装方針を含む。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（モジュール: data, strategy, execution, monitoring をエクスポート）。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 環境設定 / 設定管理
  - settings を提供する kabusys.config モジュールを実装。
    - .env ファイル（.env, .env.local）および OS 環境変数から自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env のパースロジックは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース直前の '#' をコメントとみなす）に対応。
    - 自動ロードはパッケージファイルの位置からプロジェクトルート (.git または pyproject.toml) を探索して行うため、CWD に依存しない実装。
    - 主要な必須設定値参照用プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - デフォルト値付き設定（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値等）を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値の検証）。
    - is_live / is_paper / is_dev の補助プロパティを提供。

- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini, JSON mode）にバッチ送信して銘柄別センチメント（ai_score）を計算・ ai_scores テーブルへ書き込み。
    - 時間ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30、DB 比較用に UTC naive datetime へ変換）で厳密に定義（calc_news_window）。
    - バッチ処理（デフォルト 20 銘柄／回）、1 銘柄あたりの最大記事数／文字数制限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) を実装。
    - API 呼び出しでのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフと上限回数制御を実装。
    - レスポンスの厳密なバリデーションとスコアのクリップ（±1.0）。不整合時はスキップ（例外を投げずにフェイルセーフ）。
    - DuckDB への書き込みは冪等性を考慮（該当コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を patch で差し替え可能とする設計注記。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス対策）。
    - マクロニュースは news_nlp と同様に J-Quants raw_news から抽出（マクロキーワードリスト）し、OpenAI により JSON レスポンスを期待。
    - OpenAI 呼び出しに対する堅牢なリトライ・フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等的に実行。失敗時は ROLLBACK を試行。

- データプラットフォーム（ETL / カレンダー）
  - kabusys.data.pipeline
    - ETL 実行結果を表す ETLResult dataclass を追加（取得数・保存数・品質問題・エラーの集約、to_dict メソッドを提供）。
    - ETL の差分取得・バックフィル・品質チェック（quality モジュール連携）を行う設計に基づくユーティリティを実装（差分ロジック、バックフィル日数、最小データ日等に関する定数定義）。
    - DuckDB テーブル存在チェック等のユーティリティ関数を実装。

  - kabusys.data.calendar_management
    - JPX カレンダー（market_calendar）を管理するユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
      - market_calendar が存在しない場合は曜日（土日）ベースでフォールバックする設計。
      - calendar_update_job により J-Quants から差分取得して market_calendar を冪等に保存（バックフィル・健全性チェックあり）。
    - 市場カレンダーデータの稀な NULL 値に対する警告ログや最大探索日数制限を導入し安全性を確保。

- Research（因子計算・特徴量探索）
  - kabusys.research.factor_research
    - momentum / volatility / value のファクター計算を実装。
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（必要データ不足時は None）。
      - calc_value: per, roe を raw_financials と prices_daily から取得（最新の報告日以前の財務データを参照）。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース実装。

  - kabusys.research.feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）での将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコード 3 件未満で None を返す）。
    - rank: 同順位は平均ランクで処理（小数丸めで ties 検出の安定化）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出するユーティリティ。

- 再利用性・設計品質
  - ルックアヘッドバイアス防止のため、date.today() や datetime.today() に直接依存しない設計を各所で明確化（target_date を明示的に受け取る API）。
  - 外部 API 呼び出しのフェイルセーフ化（失敗時に例外を投げずにフォールバックすることでバッチ処理の継続を重視）。
  - DuckDB をデータレイヤに採用し、SQL＋Python の組合せで計算処理を実装。
  - OpenAI 呼び出し部分はテスト容易性を意識して差し替え可能な _call_openai_api 関数を定義。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）が未設定の場合は明示的なエラー (ValueError) を発生させるチェックを実装。安全な運用を促進。

Notes / Limitations
- OpenAI（gpt-4o-mini）および J-Quants クライアントに依存するため、実行環境に適切な API キーとネットワークアクセスが必要。
- DuckDB のバージョン差異に対して互換性配慮（executemany の空リスト回避等）を入れているが、実運用ではテストが必要。
- strategy / execution / monitoring の具体実装は本差分に含まれていない（パッケージエクスポートは定義済み）。

---

開発・運用時の参考:
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しの振る舞い（リトライ・バックオフ・フォールバック）は各モジュールの定数（_MAX_RETRIES, _RETRY_BASE_SECONDS 等）で調整可能です。
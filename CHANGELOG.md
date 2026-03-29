Keep a Changelog
=================

すべての主要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」準拠で変更履歴を管理します。

0.1.0 - 2026-03-29
-----------------

初回公開リリース。以下の主要機能・モジュールを追加しました。

Added
- パッケージ情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。__version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から自動で設定を読み込む仕組みを導入（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - OS 環境変数を保護する protected バインディング（.env.local/.env の上書き制御）。
  - 必須変数確認用 _require() を実装（未設定時は ValueError を送出）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等をプロパティで取得。KABUSYS_ENV と LOG_LEVEL の値検証を実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_score）を生成。
    - バッチサイズ上限、1銘柄当たりの記事数・文字数制限、JSON レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで行う設計。部分失敗でも既存スコアを保護するため、更新対象コードのみ DELETE → INSERT を行う冪等書き込みロジック。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 表現）を提供する calc_news_window。
    - API 呼び出し箇所はテスト時に差し替え可能（ユニットテスト向けに _call_openai_api のモック推奨）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）200日移動平均乖離（重み70%）とマクロセンチメント（LLM、重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッドバイアス防止）。データ不足時は中立（1.0）扱い。
    - マクロ記事抽出、OpenAI 呼び出し、レスポンス JSON パース、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）、最終的に market_regime テーブルへ冪等書き込みを実装。
    - OpenAI クライアント生成は api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を基に営業日判定・前後営業日取得・期間内営業日列挙・SQ 日判定等のユーティリティを提供。
    - market_calendar が未登録のときは曜日（平日＝営業日）ベースでフォールバックする挙動を実装し、DB 登録値優先の一貫したロジックを保持。
    - カレンダー夜間更新ジョブ calendar_update_job を実装し、J-Quants クライアントを経由して差分取得→冪等保存（バックフィル、健全性チェックあり）。
  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧等を保持）。to_dict により品質問題はシリアライズ可能。
    - ETL パイプライン設計（差分更新、バックフィル、品質チェックの扱い、id_token 注入でのテスト容易化）に基づくインターフェースを用意。
    - jquants_client と quality モジュールを統合する想定のユーティリティを実装。
- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算する関数群を実装。
    - データ不足時の None 返却、SQL を用いた効率的なウィンドウ集計を採用。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン（複数ホライズン対応）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する設計。
- テスト容易性・運用上の配慮
  - OpenAI API 呼び出し箇所（news_nlp/regime_detector）で呼び出し関数を個別に分離し、unittest.mock で差し替え可能にしてユニットテストを容易化。
  - ルックアヘッドバイアス防止のため、各処理で date/datetime の現在時刻参照を避け、target_date で明示的に制御する設計を徹底。
  - DuckDB の executemany 空配列問題（0.10 系）に配慮した実装（空チェックを事前に行う）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Usage / Migration
- 環境変数
  - OpenAI の利用には OPENAI_API_KEY（または各関数の api_key 引数）を必ず設定してください。未設定時は ValueError が発生します。
  - 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。
  - 重要な環境変数名の例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
- DB（DuckDB）スキーマ依存
  - 多くの関数は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを参照します。利用前に想定スキーマを準備してください（DataPlatform.md / StrategyModel.md を参照）。
- フェイルセーフ
  - AI 呼び出し失敗時は例外をそのまま上位へ伝播させず、0.0 や空スコアで継続する箇所があります（news_nlp/regime_detector）。重大な DB 書き込み失敗は例外と共にロールバックされます。
- ロギング
  - 各モジュールは詳細ログ（info/warning/debug）を出力します。LOG_LEVEL による制御が可能です。

Acknowledgements / Implementation notes
- OpenAI モデルは gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）での利用を前提にレスポンスの厳密なパースロジックを実装しています。
- DuckDB をメインの分析用ローカル DB として想定。ETL やカレンダー更新は J-Quants クライアント経由での差分取得を前提に設計しています。

今後の予定（例）
- strategy / execution / monitoring パッケージの実装（発注ロジック、実行・監視機能）。
- テスト補完（ユニットテスト・統合テスト）と CI パイプライン整備。
- ドキュメント（DataPlatform.md / StrategyModel.md 参照箇所の整備）やサンプル ETL 実行シナリオの追加。
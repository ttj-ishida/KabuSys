CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)

[0.1.0] - 2026-04-02
--------------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)
  - パッケージ初期化: src/kabusys/__init__.py にて公開モジュールを定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサは export 付き、クォート（エスケープ処理）やインラインコメントを考慮。
  - protected 機能により OS 環境変数の上書きを防止。
  - Settings クラスを提供し、主要な設定・環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得。既定値・バリデーション（KABUSYS_ENV、LOG_LEVEL 等）を実装。
  - デフォルトの DB/ファイルパスや監視しきい値（CPU/MEM/DISK）などをプロパティで取得可能。
- AI モジュール (src/kabusys/ai/)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別ニュースセンチメントを算出し ai_scores へ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数のトリム、JSON Mode 利用を想定。
    - 冪等的な DB 書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の既存データ保護。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch に対応）。
    - calc_news_window(target_date) によりニュース集計ウィンドウ（JST基準の UTC naive datetime）を計算。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードに基づく raw_news フィルタ、最大記事数制限、OpenAI 呼び出しは独立実装、API 失敗時は macro_sentiment=0.0 のフォールバック。
    - レジームスコアのしきい値・スケーリングや最大リトライ／待機戦略を実装。
- Data モジュール (src/kabusys/data/)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した JPX カレンダー管理・営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索上限 (_MAX_SEARCH_DAYS) による安全策。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィルと健全性チェック実装）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分更新・保存・品質チェックのための ETLResult データクラスを実装し公開（etl.py で再エクスポート）。
    - ETL の設計方針: 営業日単位の差分取得、backfill、品質チェックは収集して上位判断へ委ねる。
    - DuckDB に対する互換性考慮（executemany の空リスト回避等）。
  - jquants_client / quality モジュールとの統合ポイントを想定（fetch/save を利用）。
- Research モジュール (src/kabusys/research/)
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比率）を計算する関数を実装。
    - prices_daily / raw_financials を参照し、結果を (date, code) キーの dict リストで返す。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）計算、rank、factor_summary（基本統計量）を実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装。
  - research パッケージの __init__ で主要関数をエクスポート。
- ロギング・設計上の配慮
  - 多くの箇所で詳細な logger メッセージを出力し、失敗時は例外伝播前にログに記録。API 失敗はフォールバックやスキップでフェイルセーフに設計。
  - ルックアヘッドバイアス防止のため各モジュールで date.today()/datetime.today() を直接参照しない設計方針を採用（target_date 引数経由）。
  - OpenAI 呼び出しは JSON モードを前提とし、厳格な JSON 出力を期待するプロンプト（SYSTEM_PROMPT）を用意。
- テスト/運用のための工夫
  - OpenAI への実際のネットワーク呼び出しを差し替えられるよう内部関数を抽象化（テストでモック可能）。
  - DuckDB を使用したローカルでのデータ操作を前提にし、ファイルパス既定値を設定。

Changed
- n/a（初回リリースのため該当なし）

Fixed
- n/a（初回リリースのため該当なし）

Security
- 重要なシークレット（OpenAI API キー等）は環境変数から取得し、Settings で必須チェックを実施。コード上にハードコーディングは行っていない。

Known limitations / Notes
- 一部機能は外部モジュール（例: kabusys.data.jquants_client, kabusys.data.quality）に依存しており、それらの実装が前提です。
- news_nlp と regime_detector は gpt-4o-mini の JSON mode を利用する想定。LLM の応答形式が崩れる場合に備えてパース回復処理やフォールバック（スコア 0.0）を実装していますが、想定外の出力が来るとスコアが欠落する場合があります。
- calc_value は PBR・配当利回りを未実装（将来の拡張点）。
- DuckDB のバージョン差異により SQL バインドの取り扱いが異なるため、executemany の空リスト回避や個別 DELETE を採用しています（互換性向上のため）。
- 全体として「観測日を外部から与える」設計（target_date 引数）を採用しており、日付の自動解決は呼び出し側で管理してください。

--- 

今後のリリースでは以下を想定:
- PBR/配当利回りなどバリューファクターの追加実装
- jquants_client / quality の具体実装とそれらに依存する ETL のエンドツーエンド動作検証
- より詳細なテストカバレッジ（LLM モック含む）と CLI/サービス化された実行スクリプトの追加
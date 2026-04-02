Keep a Changelog 準拠 — 変更履歴 (日本語)
=================================

この CHANGELOG はコードベースから推測して自動生成した内容です。各項目は実装された機能、設計方針、重要な挙動や既知の問題点をまとめています。

フォーマットは "Unreleased" とリリース単位 (ここでは v0.1.0) を含みます。

Unreleased
----------
（なし）

0.1.0 - 2026-04-02
-----------------
初回公開リリース。以下の主要機能とモジュールを実装しています。

追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダ実装。
    - 自動ロードはプロジェクトルート (.git または pyproject.toml を起点) を探索して行うため、CWD に依存しない。
    - OS 環境変数を保護する機能（protected set）を実装し、.env.local による上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサ実装:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - 行内コメントの扱い（クォートなしの場合は前の文字が空白/タブのときに '#' をコメント扱い）。
  - Settings クラスを提供（settings = Settings()）。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得。
    - KABU_API_BASE_URL のデフォルト ("http://localhost:18080/kabusapi")。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH、CPU/MEM/MEM/DISK 閾値）。
    - 環境 (KABUSYS_ENV) の検証 (development / paper_trading / live) と LOG_LEVEL 検証。
    - is_live / is_paper / is_dev ヘルパー。

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日ロジック:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - DB データ優先、未登録日は曜日ベースのフォールバック。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) による安全策。
      - calendar_update_job: J-Quants API から差分取得して idempotent に保存。バックフィルと健全性チェックあり。
  - ETL パイプライン:
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラーの集約）。
    - pipeline モジュールに ETL のユーティリティ（差分更新、品質チェック設計方針の実装方針）。
  - etl.py: pipeline.ETLResult を再エクスポート。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20 日）、20 日平均売買代金・出来高比などの計算を実装。
    - DuckDB の SQL ウィンドウ関数を用いた効率的実装。
    - calc_momentum / calc_volatility / calc_value を提供し、date, code をキーとする辞書リストを返す設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズンのサポート、入力バリデーション）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）。
    - rank ユーティリティ（平均ランク，同順位は平均ランク処理）。
    - factor_summary（count, mean, std, min, max, median の統計要約）。
  - 依存: DuckDB 接続を引数に取り、外部 API にアクセスしない設計。

- AI / NLP 機能 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）で評価、結果を ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ送信（最大 20 銘柄/コール）、1 銘柄につき最新最大10記事・最大3000文字でトリム。
    - JSON mode を使用し、レスポンスのバリデーションとスコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフによるリトライ。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップし処理継続。
    - テスト用フック: _call_openai_api をモック可能（unittest.mock.patch を想定）。
  - regime_detector.score_regime:
    - ETF 1321（Nikkei-225 連動 ETF）200 日移動平均乖離（重み70%）とニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - LLM コールは記事がある場合のみ行う。API 失敗時は macro_sentiment=0.0 として継続。
    - lookahead バイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - リトライと 5xx 判定を行う堅牢な API 呼び出し実装。
    - テスト用フック: _call_openai_api をモック可能。

改善 (Changed)
- 設計上の細かな配慮点を実装:
  - ルックアヘッドバイアス防止のため、全 AI / 研究系処理で datetime.today() / date.today() を参照しない設計。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装し、ROLLBACK の失敗もログに記録。
  - DuckDB の executemany に関する制約を考慮（空リストの扱いを回避）した実装。

修正 / 堅牢化 (Fixed)
- AI 呼び出しの障害耐性を強化:
  - json パースエラー、キー欠落、数値変換エラーなどは警告ログを出力してフェイルセーフ値にフォールバックし例外を投げない。
- .env 読み込みのエラー（ファイルオープン失敗）を warnings.warn で通知し処理継続。

セキュリティ関連 (Security)
- OpenAI API キーの扱い:
  - API キーは関数引数 (api_key) から注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。
  - 必須の公開環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings により取得時に存在チェックを行い、未設定なら ValueError を送出する。
- .env 読み込み時に OS の環境変数を protected として上書きを防ぐ機構を実装。

テストフレンドリネス
- OpenAI 呼び出し部分 (_call_openai_api) をモック可能に設計してユニットテストを容易にしている。
- 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

既知の問題 (Known issues)
- src/kabusys/data/pipeline.py の終端付近でソースが途中で切れているように見え、_get_max_date の戻り値部分で "return date.fro" のような断片が存在します。これは構文エラーおよび未実装／不完全な実装を引き起こす可能性があるため修正が必要です（CI や実行時に致命的な例外に繋がります）。
- 一部の機能は前提となる DuckDB のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）に依存しており、該当テーブルが存在しない場合の取り扱い（None を返す / ログ出力）などの動作はドキュメント通りですが、実運用前にスキーマ準備が必要です。

利用上の注意 / 重要な動作
- news_nlp / regime_detector は OpenAI の JSON mode（response_format={"type": "json_object"}）を前提としているため、API の仕様変更やモデルの応答形式変化により脆弱になる可能性があります。
- score_news と score_regime は target_date 引数に明示的な日付を渡す設計になっており、実行日時に依存しない (再現性のある) 動作を目指しています。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を利用する想定。該当クライアントの実装や API レスポンス仕様に依存します。

将来の改善提案（参考）
- pipeline.py の未完了箇所の修正と、ETL の end-to-end テストを追加。
- OpenAI レスポンスのスキーマ検証をさらに厳格化（JSON schema 等）して誤応答に対する耐性を向上。
- DuckDB テーブル作成セルフチェックユーティリティの追加（必要なテーブル・カラムが不足している場合の自動警告）。
- monitoring サブパッケージの実装・公開（__all__ に含まれているがコード未提供の可能性があるため確認）。

脚注
- 本 CHANGELOG は提供されたソースコードから仕様や実装の意図を推測して作成しました。実際のリポジトリのコミット履歴や設計ドキュメントと差異がある場合があります。正確な履歴は元の VCS ログを参照してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリの初期リリース (0.1.0) に含まれる主な機能・設計方針・注意点を日本語でまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームの基盤となるモジュール群を実装しました。主な内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの導入（__version__ = 0.1.0）。
  - サブパッケージ公開: data, research, ai, その他（__all__ にて定義）。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込みを実装。
    - プロジェクトルート識別は __file__ の親ディレクトリから `.git` または `pyproject.toml` を探索して決定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサ実装: `export KEY=val`、シングル/ダブルクォート内のエスケープやインラインコメントの処理をサポート。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants、kabuステーション、Slack、DB パスなどのプロパティ（必須項目は未設定時に ValueError）。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のヘルパー。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX 市場カレンダー管理（market_calendar テーブル連携）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存する夜間バッチ処理（バックフィル、健全性チェックを実装）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
  - pipeline / etl
    - ETL パイプライン関連：差分取得、保存、品質チェックの骨格。
    - ETLResult データクラス（実行結果の構造化、品質問題やエラーの集約、to_dict）。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得等。
    - jquants_client 経由のデータ保存フローを想定（Idempotent な save_* 関数に依存）。

- ニュース NLP / AI (kabusys.ai)
  - news_nlp
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を正しく UTC に変換して扱う（calc_news_window）。
    - バッチ送信（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事数上限、文字数トリム等のトークン肥大化対策を実装。
    - JSON Mode の応答バリデーション、レスポンス復元処理（余分な前後テキストから最外側の JSON を抜く）を実装。
    - 再試行ポリシー: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。失敗時は部分的にスキップして継続（フェイルセーフ）。
    - DuckDB に対する DELETE → INSERT の置換ロジック（部分失敗時に既存スコアを保護）。
  - regime_detector
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し market_regime テーブルへ書き込み。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立値 1.0 を採用）。
    - マクロニュース抽出（マクロキーワード群）と LLM 評価（gpt-4o-mini）。API エラー時は macro_sentiment=0.0 にフォールバック。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- リサーチ/ファクター分析 (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を DuckDB SQL で計算。
    - calc_volatility(conn, target_date): 20 日 ATR（true range）、ATR 比率、20 日平均売買代金、出来高比を計算。
    - calc_value(conn, target_date): raw_financials から直近財務を取得して PER, ROE を計算。
    - SQL ベース実装で、prices_daily / raw_financials のみ参照。本番発注 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。データ不足時は None を返す。
    - rank(values): 同順位は平均ランクで処理（小数丸めで ties を安定検出）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティと運用上の注意
- OpenAI API キー（OPENAI_API_KEY）や各種トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）は必須の設定項目があり、未設定時は ValueError が発生します。運用前に .env を用意してください（.env.example を参照）。
- 自動 .env 読み込みは OS 環境変数を上書きしないよう保護されます（プロセス起動時の既存環境変数が優先されます）。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### 既知の制約・設計上の配慮
- データストアは DuckDB を前提とした実装です。テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を用意する必要があります。
- ニュース・レジームの LLM 呼び出しは gpt-4o-mini を想定した JSON Mode を利用する想定です。OpenAI SDK のバージョン差異により例外クラスや status_code の扱いが異なるため、耐性を持たせた実装をしていますが、実運用前に SDK 互換性の確認を推奨します。
- ルックアヘッドバイアス防止のため、date ベースの引数で処理を行い、内部で datetime.today() や date.today() を参照しない設計になっています。
- ETL / API 呼び出しは部分失敗を許容する（フェイルセーフ）方針です。致命的エラーは ETLResult.errors に集約されますが、品質チェック（quality module）はエラー重大度を返しても処理を続行する設計です。

---

この CHANGELOG はコードの実装内容から推測して記載しています。追加の機能やバグ修正が行われた場合は本ファイルを更新してください。
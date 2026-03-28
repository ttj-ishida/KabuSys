# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = 0.1.0）。
  - public API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護するための protected キー処理（.env.local の上書き制御）。
  - Settings クラスを提供し、必須項目の取得（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）、パス設定（DUCKDB_PATH, SQLITE_PATH）、環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーションを行う。

- AI / ニュースNLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を評価する score_news を実装。
  - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
  - バッチ（最大 20 銘柄）処理、記事数・文字数トリム対応（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - リトライ・指数バックオフ（429 / ネットワーク断 / タイムアウト / 5xx）を実装。
  - レスポンス検証（JSON 抽出、results フィールド、コード一致、数値検証）を行い、有効なスコアのみ ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
  - API 呼び出しポイントをユニットテスト容易に差し替え可能（kabusys.ai.news_nlp._call_openai_api）。

- AI / 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ma200_ratio 計算、マクロキーワードでの raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）の実装。
  - API 失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ。
  - 市場レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - news_nlp と独立した _call_openai_api 実装によりモジュール結合を抑止、テスト用差し替えも可能。

- Data: ETL / パイプライン (kabusys.data.pipeline, etl)
  - ETLResult データクラスを公開し、ETL 実行結果（取得・保存件数、品質問題、エラー概要）を構造化して返却。
  - 差分取得・バックフィル・品質チェックの方針に沿ったユーティリティ実装（テーブル存在チェック、最大日付取得など）。
  - ETL 関連の公開インターフェースを etl モジュールで再エクスポート。

- Data: カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー管理ユーティリティを実装：market_calendar を参照した is_trading_day、is_sq_day、next_trading_day、prev_trading_day、get_trading_days を提供。
  - J-Quants からの差分取得を行う calendar_update_job（バックフィル・健全性チェック・保存処理）。
  - market_calendar が未取得の場合は曜日ベースのフォールバックを使用する安全設計。

- Research（因子・特徴量探索）
  - factor_research: calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（20日 ATR、相対 ATR、出来高・売買代金指標）、calc_value（PER/ROE）を実装。すべて DuckDB SQL で計算し読み取り専用（実行系へアクセスしない）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（Spearman ランク相関での IC 計算）、rank（同順位は平均ランク）、factor_summary（統計サマリー）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- 共通設計方針・ユーティリティ
  - DuckDB をデータ層に採用し、SQL と Python の組合せで主要計算を実装。
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を参照しない箇所（スコアリング関数等）を明示。
  - 例外ハンドリング・ログ出力を重視し、API 失敗時は例外を投げずフォールバックまたは部分スキップする設計（フェイルセーフ）。
  - テスト性向上のため API 呼び出し箇所を差し替え可能な実装にしている（ユニットテスト用 patch）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。ただし実装内において以下の堅牢化を行っている点を明示:
  - .env 読み込みでファイルオープン失敗時に警告を出してスキップする。
  - DuckDB executemany の空リストバインド問題に対するガード（空時は実行しない）。
  - DB 書き込み失敗時は ROLLBACK を試み、ROLLBACK 自体が失敗した際には警告ログを出力する防御的コード。

### 削除 (Removed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 機密情報（OpenAI API キー等）は環境変数を介して注入し、設定管理で必須チェックを行う実装。自動 .env ロードで OS 環境変数を保護する仕組みあり（.env.local 上書き制御で protected keys を尊重）。

---

注意事項・既知の制約
- OpenAI 呼び出しは有償 API に依存する（gpt-4o-mini を想定）。API キー未設定時は該当関数が ValueError を投げるため、実運用時には環境変数 OPENAI_API_KEY または api_key 引数の注入が必要です。
- DuckDB バージョン差異による SQL バインド挙動を考慮した実装（executemany の空リスト回避など）を行っていますが、実環境での互換性検証を推奨します。
- news_nlp / regime_detector は LLM の応答形式に強く依存するため、LLM の出力仕様変更時はパーサー側の調整が必要になる可能性があります。

もし特定のモジュールごとにより詳細なリリースノートや利用例、互換性情報が必要であれば、どのモジュールについて深掘りするか教えてください。
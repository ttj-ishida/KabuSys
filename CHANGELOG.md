# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠します。

なお、本CHANGELOGはソースコードの内容から推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しています。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ全体
  - パッケージ初期バージョンを設定（kabusys v0.1.0）。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動 .env ロードを実現。
  - .env パーサを実装（export 形式、クォート内エスケープ、インラインコメント処理をサポート）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須設定取得 helper (_require) と Settings クラスを提供。以下の主要設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - Settings に is_live / is_paper / is_dev のプロパティを追加。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
  - タイムウィンドウ計算（JST 前日15:00〜当日08:30）と UTC 変換ユーティリティを実装（calc_news_window）。
  - バッチ処理（最大 20 銘柄 / API 呼び出し）・1 銘柄あたり記事数/文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - エラー扱い（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフリトライを実装。
  - レスポンスのバリデーション処理を実装（JSON 抽出、results 配列検証、コード整形、数値検証、スコアの ±1.0 クリップ）。
  - DuckDB への冪等書き込みロジック（DELETE → INSERT、部分失敗時の保護）を実装。
  - テスト容易性のため、内部の OpenAI 呼び出しを置換可能（_call_openai_api を patch できる設計）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - prices_daily / raw_news / market_regime を参照し、レジームスコアを計算して market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - OpenAI 呼び出し用の独立実装（news_nlp とプライベート関数を共有しない）。
  - API 呼出失敗やレスポンスパース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。
  - リトライ処理、ログ出力、しきい値によるラベリングを実装。

- データ基盤（kabusys.data）
  - ETL パイプライン基盤（pipeline モジュール）を実装。
  - ETLResult データクラスを public API として再エクスポート（kabusys.data.etl）。
    - ETL の取得数・保存数、品質検査結果、エラー一覧を保持。
    - has_errors / has_quality_errors プロパティおよび to_dict を提供。
  - market_calendar を管理するカレンダーモジュール（calendar_management）を実装。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未登録日の曜日ベースフォールバック、最大探索日数制限で無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得・バックフィル・保存（fetch/save の呼び出しと例外ハンドリング）。
    - 健全性チェック（将来日付が異常な場合 skip）を実装。
  - ETL パイプライン（pipeline）:
    - 差分更新ロジック、デフォルト backfill の実装、品質チェック（quality モジュール）との連携。
    - 最終取得日の取得ユーティリティ、テーブル存在チェック等を提供。

- 研究モジュール（kabusys.research）
  - ファクター計算（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS 0 や欠損で None）。
    - DuckDB 上で SQL とウィンドウ関数を使って効率的に算出する設計。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマン（ランク）相関による IC 計算（最小有効レコード数チェック）。
    - rank: 同順位は平均ランクで扱うランク化関数（丸めによる ties 対応）。
    - factor_summary: 各カラムの基本統計量（count, mean, std, min, max, median）を計算。
  - 研究向けユーティリティを public export（zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- n/a（初回リリースのため過去との互換性変更はなし）

### 修正 (Fixed)
- n/a（初回リリース）

### 削除 (Removed)
- n/a（初回リリース）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で注入可能。環境変数 OPENAI_API_KEY に依存する場合の未設定は ValueError を投げる仕様になっているため、キー漏洩・誤設定に注意が必要。
- .env 自動読み込みは環境変数で無効化可能（テストや CI でのキー流出を抑止するための配慮）。

### 既知の制約・注意点 (Notes)
- 多くの処理は DuckDB のテーブル（prices_daily, raw_news, market_regime, raw_financials, news_symbols, ai_scores, market_calendar 等）を前提にしており、事前にスキーマ／データが必要です。
- OpenAI（gpt-4o-mini）と J-Quants クライアントへの実際の API 通信が発生する機能があるため、本番では API キー／ネットワークの取り扱いに注意してください。
- news_nlp と regime_detector は OpenAI 呼出し関数を意図的に独立実装しており、テスト時はモックで差し替え可能です。
- research モジュールは外部発注や取引 API に影響を与えない（読み取り専用）設計。
- DuckDB の executemany 空リストの制約（0.10 等）を回避するためのガードロジックを実装。

---

今後のリリースでは以下を予定（推測）:
- strategy / execution / monitoring サブパッケージの具体的な戦略・発注・監視実装。
- テストカバレッジの追加、型アノテーション強化。
- ドキュメント（Usage / Deployment / Data schema）の充実。

LICENSE、CONTRIBUTING、ドキュメントに関する正式な情報はリポジトリの他ファイルを参照してください。
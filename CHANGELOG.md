# Changelog

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
重要: この CHANGELOG は与えられたコードベースから推測して作成したものであり、実際のコミット履歴に依存していません。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ基本構成
  - kabusys パッケージ（サブパッケージ: data, ai, research, execution, monitoring を公開）。
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）。

- 環境設定/管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートを .git または pyproject.toml から探索し、CWD に依存しない実装。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート中のバックスラッシュエスケープ
    - インラインコメントの扱い（クォート有無での判定ルール）
  - 既存 OS 環境変数を保護するための protected 上書き制御。
  - Settings クラスを提供（プロパティ経由で必須トークンやパスを取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
    - duckdb/sqlite データベースパスのデフォルト
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事のセンチメント解析（score_news）
    - gpt-4o-mini を用いた JSON Mode での LLM 呼び出し。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - 銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で API 送信。
    - 1銘柄あたりの記事/文字数上限（記事数: 10、文字数: 3000）によるトリム。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時の安全な DB 書き換え（DELETE → INSERT）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ実装。
    - テスト用のフック: _call_openai_api を patch で差し替え可能。
  - regime_detector: 市場レジーム判定（score_regime）
    - ETF 1321（Nikkei225 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news をフィルタしてタイトルを LLM に投げる（上限 20 記事）。
    - OpenAI 呼び出しは独立実装（news_nlp と共通のプライベート関数を共有しない設計）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、および API フェイルセーフ（失敗時は macro_sentiment=0.0 として継続）。
    - リトライ / エラーハンドリング実装（RateLimit, 接続エラー, タイムアウト, 5xx 他）。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日ユーティリティ
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未登録の場合は曜日ベースのフォールバック（週末を非営業日とする）。
    - calendar_update_job: J-Quants API からの差分取得 → market_calendar へ冪等保存。バックフィル・健全性チェックを実装。
  - pipeline: ETL パイプライン補助
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を標準化。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client, quality モジュールと連携）。
  - etl モジュールで ETLResult を公開。

- Research（kabusys.research）
  - factor_research: ファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率等。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（データ不足時は None）。
    - DuckDB 上で SQL と Python を組み合わせて実装。外部 API へはアクセスしない設計。
  - feature_exploration: 研究用ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。データ不足（<3 件）で None を返す。
    - rank: 同順位は平均ランクとするランク関数（丸め処理で ties 判定の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。
  - research パッケージから主要関数を再エクスポート。

- ロギング & DuckDB
  - 各モジュールで適切に logger を使用し、重要イベント・ワーニング・例外をログ出力。
  - DuckDB をデータ格納/クエリの前提とした実装。

- テストしやすさの配慮
  - OpenAI 呼び出し部分に対して patch 可能な内部関数（_call_openai_api）を用意。
  - API キーは関数引数で注入可能（api_key 引数 or 環境変数 OPENAI_API_KEY）。

### Fixed
- API 呼び出し失敗やレスポンスパース失敗時のフォールバック処理を多数実装（例: LLM 失敗時はスコア 0.0 として継続）。
- 部分失敗時に既存 DB データを誤って消さないように、ai_scores の置換はスコア取得済みコードのみを対象に DELETE → INSERT を実施。

### Changed
- 初版のため該当なし。

### Known limitations / Notes
- OpenAI 依存:
  - gpt-4o-mini を使用する設計。利用には有効な OPENAI_API_KEY（または api_key 引数）が必要。未設定時は ValueError を送出。
- calendar_update_job は実行時に system date（date.today）を参照する（バッチスケジューリング前提）。
- 一部 SQL の挙動は DuckDB バージョンに依存する（例: executemany の空パラメータ制約やリスト型バインドの挙動に対する互換性配慮）。
- 本リリースでは発注・実行（kabu ステーション等）に関する実装は本コード内で設定取得や定義はあるが、実取引に関する外部 API 呼び出しや実行ロジックは分離されている（安全配慮）。

### Security
- 環境変数による機密情報取得（トークン等）を前提としているため、.env の取扱いやリポジトリ公開時の取り扱いに注意が必要。

---

（補注）詳細な変更履歴はコミットログに基づいて作成することを推奨します。本 CHANGELOG は与えられたソースコードの設計・実装から推測して作成した概要です。
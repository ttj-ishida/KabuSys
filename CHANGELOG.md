# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
初期リリースでは主に機能追加をまとめています。

## [0.1.0] - 2026-03-29

### 追加
- パッケージ全体
  - kabusys パッケージの初期リリース。バージョン 0.1.0 をパッケージメタデータに設定（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring（__all__ に定義。個別実装は別途）。

- 設定・環境読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env の細かいパース対応:
    - コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 環境変数検証・取得ヘルパー:
    - 必須項目取得時に未設定なら ValueError を送出する _require。
    - 許容値チェック（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルト設定:
    - KABUSYS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等のデフォルト値を提供。

  - 必須環境変数（主な例）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - OPENAI_API_KEY は AI 機能呼び出し時に必要（関数引数でも注入可能）

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini / JSON Mode）で銘柄ごとのセンチメントを算出する score_news(conn, target_date, api_key=None) を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB 検索）。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事トリミング（記事数・文字数制限）、レスポンス検証、±1.0 クリップを実装。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを導入。非再試行エラーはスキップして継続。
    - DuckDB に対して idempotent な書き込み（DELETE → INSERT）を行い、部分失敗でも既存スコアを保護。
    - テスト向けに _call_openai_api の差し替え（patch）を想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で 'bull' / 'neutral' / 'bear' を判定する score_regime(conn, target_date, api_key=None) を実装。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースは raw_news からキーワードフィルタで取得（キーワードリストを内包）。
    - OpenAI 呼び出しは独立実装、最大リトライ・バックオフ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を保証。

- データ基盤（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装（J-Quants クライアント呼び出しで差分取得 → 保存）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を休業日とみなす）。
    - 最大探索日数制限や健全性チェック、バックフィル期間の扱いを実装。
  - ETL パイプラインの公開インターフェース（src/kabusys/data/etl.py / pipeline.py）
    - ETLResult データクラスを実装（取得/保存件数、品質問題一覧、エラー一覧等を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）の方針を実装。DuckDB の存在チェックや最大日付取得ヘルパーを実装。
    - デフォルトの backfill ロジック、カレンダー先読み、エラー集約方針（Fail-Fast ではなく問題を収集）を反映。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials の最新財務データと価格を組み合わせて PER / ROE を計算。
    - DuckDB 上の SQL とウィンドウ関数を活用し営業日ベースの窓処理を実装。データ不足時は None を返す挙動を採用。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を一度に取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（サンプル数不足時は None）。
    - rank(values): 同順位は平均ランクになるランク化関数（丸めで ties 検出誤差を軽減）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ関数。
  - リサーチ用ユーティリティは外部依存を極力排し標準ライブラリのみで実装。

### 変更
- 初期リリースのため過去の変更は無し。

### 修正
- 初期リリースのため修正は無し。

### 削除
- 初期リリースのため削除は無し。

### セキュリティ
- 初期リリース。OpenAI の API キー等の取り扱いは環境変数で行い、.env 自動読み込みでは OS 環境変数を保護する機能（protected set）を実装。

### 既知の注意点 / 設計上の重要事項
- ルックアヘッドバイアス防止:
  - AI モジュール、リサーチ、ETL 等の多くは datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計になっています。運用・テスト時は target_date を明示的に指定してください。
- フェイルセーフ設計:
  - OpenAI 呼び出し失敗時は例外を投げずフォールバック（0.0 スコア等）で継続する場面が多くあります。運用ではログを監視してください。
- DuckDB 互換性注意:
  - executemany に空リストを渡すと失敗するバージョン対策（空チェックを実装）。
  - 一部 SQL は DuckDB の型/戻り値の挙動に依存しており、値の変換処理（date 変換等）を行っています。
- テスト容易性:
  - OpenAI 呼び出しの窓口関数はモジュール内で分離してあり、unittest.mock.patch で差し替え可能です。
- 必須環境変数未設定時は ValueError を送出する箇所があるため、運用前に .env/.env.local または環境変数を適切に設定してください。

--- 

開発・運用で追加してほしい項目（例: 互換性情報、リリース日変更、マイグレーション手順等）があれば指示ください。必要に応じて Unreleased セクションや過去のリリース履歴を追記します。
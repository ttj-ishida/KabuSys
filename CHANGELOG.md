# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys 以下）の実装内容から推測して作成した初回リリース向けの変更履歴です。

全般的な設計方針（概略）
- DuckDB を主要なデータストアとして利用（prices_daily / raw_news / ai_scores / market_regime / market_calendar 等）。
- ルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照せず、関数引数で基準日を受け取る設計。
- 外部 API 呼び出し（OpenAI / J-Quants など）はリトライ（指数バックオフ）やフォールバックを備え、失敗時は例外を直接伝播させないか安全なデフォルト値（例: macro_sentiment=0.0）で継続する設計。
- テスト容易性のため、OpenAI 呼び出しなどを差し替え可能（関数を patch する想定）に実装。

[0.1.0] - 2026-03-31
Added
- パッケージ全体
  - 初回リリース（バージョン 0.1.0）。パッケージメタ情報: __version__ = "0.1.0"。
  - 主要サブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ により公開）。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local ファイルの自動読み込み機能を実装。読み込み優先度: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートのエスケープ処理対応。
    - コメント（#）処理（クォートあり/なしでの扱い差）を実装。
  - _load_env_file に protected 引数を導入し、既存 OS 環境変数を上書き保護。
  - Settings クラスを実装し、アプリケーション設定値をプロパティとして提供:
    - 必須キー取得の明示的チェック (_require): JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
    - デフォルト付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
    - env / log_level に対するバリデーション（許容値チェック）。is_live / is_paper / is_dev のヘルパーも提供。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None)
      - ニュース収集ウィンドウ計算: JST 基準で「前日 15:00 ～ 当日 08:30」（内部では UTC naive datetime を返す calc_news_window）。
      - news_symbols + raw_news を銘柄単位で集約し、1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE (=20) 銘柄ごとに OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信。
      - リトライ方針: RateLimitError / 接続エラー / タイムアウト / 5xx は指数バックオフで再試行。その他は失敗してもスキップ。
      - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の整合性、数値検証）。スコアは ±1.0 にクリップ。
      - 書き込みは部分置換（DELETE WHERE date=? AND code=? を executemany → INSERT）で idempotent に保存。空リスト executemany 回避等 DuckDB の互換性を考慮。
      - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成してレジーム（bull/neutral/bear）を判定。
      - 重み付け: MA 70%（スケール係数 10 を乗じる）、マクロ 30%。
      - LLM 呼び出しは gpt-4o-mini を使用。API 呼出しは独立実装（news_nlp の内部呼出しと共有しない）。
      - LLM 失敗時は macro_sentiment=0.0 にフォールバック。
      - 判定結果を market_regime テーブルに冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み。
      - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar テーブルが存在しない場合は曜日ベース（週末除外）のフォールバックを使用。
    - next/prev_trading_day は最大探索範囲を制限して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job(conn, lookahead_days=90): J-Quants からの差分取得・保存フローを実装（バックフィル、健全性チェック、fetch/save の例外ハンドリング）。
  - ETL パイプライン（kabusys.data.pipeline と etl）
    - ETLResult データクラスを追加（取得/保存件数、品質チェック結果、エラー一覧を管理）。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality と連携する想定）の方針とユーティリティを実装。
    - _get_max_date / _table_exists 等のテーブル確認ヘルパーを実装。
  - etl モジュールから ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率 等を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を結合し PER / ROE を算出（EPS が 0 / 欠損時は None）。
    - 実装は SQL（DuckDB）中心で、営業日ベースの窓（horizons 等）を考慮。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。horizons の検証（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。3 レコード未満で None。
    - rank(values): 同順位は平均ランクを返す実装（丸めで ties を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する簡易統計。

- 内部実装の注意点・フェイルセーフ
  - OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用し、パース失敗や余分な前後テキストに対しても復元ロジックを実装。
  - API エラーの扱い:
    - RateLimitError / APIConnectionError / APITimeoutError / 5xx はリトライ対象（指数バックオフ）。
    - 非 5xx の APIError はリトライせず失敗として扱う。
    - リトライ全消費時は警告ログを出し、安全なフォールバック値で継続（例: macro_sentiment=0.0、または空スコアでスキップ）。
  - DuckDB 向け互換性考慮:
    - executemany に空リストを渡さないチェック。
    - 一部クエリで ROW_NUMBER / window 関数を使用して互換性を保つ。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

注意 / マイグレーションガイド（本リリースを使い始める際のポイント）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の _require により未設定時は ValueError）。
- OpenAI API キー:
  - score_news / score_regime は api_key 引数優先。未指定時は環境変数 OPENAI_API_KEY を参照する。
- .env 自動ロード:
  - パッケージはインストールパスからプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。CI/テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - 本実装は特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とします。ETL 系の関数を利用する前にスキーマを用意してください。

貢献・テストについて
- OpenAI 呼び出し部はテスト時にパッチ差し替え可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- ETLResult.to_dict() により監査ログや CI の検証が容易に行えます。

今後の予定（候補）
- PBR・配当利回り等のバリューファクター追加。
- モデル・パフォーマンス計測用のログ/メトリクス機能拡張。
- J-Quants / kabu API クライアントの抽象化と再利用性向上。

---
（この CHANGELOG はコード内容からの推測に基づく生成物です。実際のリリースノートとして使用する場合は、必要に応じて実装者の意図や変更履歴を反映して編集してください。）
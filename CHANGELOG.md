CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」形式に従い、セマンティックバージョニングを採用します。

Unreleased
----------

（開発中の変更はここに記載してください）

0.1.0 - 2026-03-29
-----------------

初回リリース（初期実装）。以下の機能群と主要実装を追加しました。

Added
-----

- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージ構成: data, research, ai, monitoring, strategy, execution を想定したエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から再帰的に探索する機能を実装（配布後も CWD に依存しない）。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサ実装: export プレフィックス対応、クォート内のバックスラッシュエスケープ、コメント処理などをサポート。
  - 上書き時に OS 環境変数を保護する protected set の導入。
  - 必須設定取得ヘルパー _require と Settings クラスを実装。以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini／JSON Mode）へバッチ送信してセンチメント（ai_score）を算出。
  - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime に変換して比較）。
  - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたり記事上限/文字上限によるトリム処理実装。
  - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
  - レスポンス検証: JSON 抽出／検証（results 配列、code と score の検証）、スコアを ±1.0 にクリップ。
  - DuckDB への冪等書き込み（DELETE → INSERT）を実装。executemany の空リストに対する互換性対策あり。
  - API キーは引数で注入可能（テスト容易化）。未設定時は環境変数 OPENAI_API_KEY を参照して ValueError を送出。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - 日次単位で市場レジーム（"bull"/"neutral"/"bear"）を判定し market_regime テーブルへ保存。
  - レジーム判定は ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成。
  - マクロニュースは news_nlp.calc_news_window により得たウィンドウのタイトルをフィルタして使用。
  - OpenAI 呼び出しは gpt-4o-mini、JSON モード使用。API エラー時は macro_sentiment=0.0 にフォールバック（例外は上げない）。
  - DuckDB への冪等トランザクション処理（BEGIN/DELETE/INSERT/COMMIT、例外時に ROLLBACK）を実装。
  - ルックアヘッドバイアス回避の設計（date < target_date を使用、datetime.today() を参照しない）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算。必要行数未満は None。
    - calc_value: raw_financials から直近の財務データを取得し PER, ROE を算出。
    - SQL と DuckDB ウィンドウ関数で実装（外部 API 不使用）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクを与えるランク関数（丸めを行い ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出。
  - すべて標準ライブラリと DuckDB のみで実装（pandas 等に依存しない）。

- データ層（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - 営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - market_calendar がない場合の曜日ベースのフォールバックを提供。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得して market_calendar を更新（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル、先読み日数などの制御定数を導入。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得・保存・品質チェックの設計を実装（jquants_client と quality モジュールを利用）。
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得、営業日調整ロジックなど。

- テストフック / 実装上の配慮
  - OpenAI 呼び出し箇所は _call_openai_api を経由する設計で、unittest.mock.patch で差し替え可能（テスト容易化）。
  - API 失敗時は例外を上位に伝播させずフェイルセーフ挙動（ニュース/マクロスコアは 0.0、スコア取得失敗はスキップ）。

Changed
-------

- 初回リリースのため該当なし。

Fixed
-----

- 初回リリースのため該当なし。

Deprecated
----------

- 初回リリースのため該当なし。

Removed
-------

- 初回リリースのため該当なし。

Security
--------

- 初回リリースのため該当なし。

Notes / Known limitations
-------------------------

- DuckDB を前提に SQL 実装しており、対象テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）のスキーマ依存があるため、テーブル定義が揃っていることが前提です。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、JSON Mode を利用する設計です。API 仕様変更により挙動が変わる可能性があります。
- ai/news の JSON 解析は余分な前後テキストを取り除く耐性を持ちますが、LLM の出力が大きく逸脱した場合はスキップされることがあります。
- .env パーサは一般的なシェル形式に合わせた実装ですが、特殊なケースは未カバーの可能性があります。
- 現フェーズでは PBR・配当利回りなど一部バリューファクターは未実装。

Migration / Upgrade notes
-------------------------

- なし（初回リリース）。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID のいずれかは実行する機能により必須になります。settings の _require により未設定で ValueError が発生します。
- 自動 .env ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献・今後の予定
----------------

- モデル選定やプロンプトの改善、LLM レスポンス検証の強化。
- 追加ファクター（PBR、配当利回り等）の実装。
- より細かい品質チェックと監視（monitoring）・自動発注（execution）モジュールの実装拡張。
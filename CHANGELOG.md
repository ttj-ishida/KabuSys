CHANGELOG
=========

このファイルは「Keep a Changelog」仕様に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

すべての変更はセマンティックバージョニングに従います。

Unreleased
----------

（未リリースの変更はここに記載します）

v0.1.0 — 2026-03-26
-------------------

Added
- 初期リリース: kabusys パッケージ（日本株自動売買システム）を追加。
  - パッケージ構成: data, research, ai, config などのモジュール群を提供。
- 環境設定（kabusys.config）:
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - export KEY=val 形式、クォート文字列（バックスラッシュエスケープ考慮）、コメント処理等に対応するパーサを実装。
  - OS 環境変数を保護する protected 機能（.env の上書きを防止）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定値をプロパティで取得。KABUSYS_ENV と LOG_LEVEL の値検証を行う。
  - デフォルト DB パス: DuckDB "data/kabusys.duckdb", SQLite "data/monitoring.db"。
- AI モジュール（kabusys.ai）:
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチセンチメント評価を行う。
    - バッチサイズ、1銘柄あたりの記事数・文字数上限を設け（BATCH_SIZE=20, MAX_ARTICLES_PER_STOCK=10, MAX_CHARS_PER_STOCK=3000）。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密検証（JSON 抽出、results キー、code/score 型チェック）、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは部分的失敗に備え、対象コードのみ DELETE → INSERT の冪等操作を実行（トランザクション、空パラメータ回避のため executemany 前のチェック）。
    - calc_news_window: JST ベースのニュースウィンドウを UTC naive datetime に変換するユーティリティを提供。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付け合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードフィルタで抽出し、OpenAI（gpt-4o-mini）に JSON 出力を要求。
    - API の失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。リトライ処理・5xx 判定に対応。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）、失敗時は ROLLBACK を試行。
    - ニュース NLP モジュールと OpenAI 呼び出し実装を分離し、モジュール結合を避ける設計。
- Research モジュール（kabusys.research）:
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日MA乖離）を SQL ウィンドウ関数で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range の NULL 伝播を考慮）、atr_pct、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新報告値（target_date 以前）と価格を組み合わせて PER, ROE を算出。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons のバリデーションあり。
    - calc_ic: ランク相関（Spearman ρ）を計算。None 値除外、サンプル数不足時は None。
    - rank: 同順位は平均ランクで処理、floating rounding により ties の判定安定化を実装。
    - factor_summary: count/mean/std/min/max/median を None 除外で算出。
- Data モジュール（kabusys.data）:
  - calendar_management:
    - JPX カレンダーの管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。market_calendar がない場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS 再取得）、健全性チェック、jquants_client を利用した保存（冪等）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。
  - pipeline / etl:
    - ETLResult データクラスを追加（取得数・保存数・品質チェック・エラー収集など）。
    - _get_max_date / _table_exists 等の ETL ヘルパーを実装。デフォルトバックフィル日数等を定義。
  - etl モジュールから ETLResult を再エクスポート。

Changed
- 共通設計方針（コード全体）:
  - ルックアヘッドバイアス回避のため、各処理は datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を用いた SQL 中心の集計/計算を採用し、外部 API 呼び出し（発注等）は行わない研究用コードの分離。
  - ロギングを充実させ、フェイルセーフにより API エラー時も処理を継続（ログ出力）する方針。

Fixed
- news_nlp / pipeline:
  - DuckDB の executemany が空リストを受け付けない点を考慮し、空パラメータ時の実行回避ロジックを追加。
- OpenAI 関連の例外ハンドリングを強化:
  - APIError の status_code を安全に取得するため getattr を使用し、5xx 系と非5xx 系で挙動を分岐。
  - JSON パース失敗時にレスポンスの最外側の {} を抽出して復元するフォールバックを追加（JSON mode でも前後テキスト混入に対応）。
- config パーサ:
  - クォート内のバックスラッシュエスケープ処理と、クォートなしの inline コメント認識ルールを明確化して堅牢化。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を使用し、JSON Mode（response_format={"type": "json_object"}）でのやり取りを想定。
- テスト容易性のため、AI 呼び出しの内部ラッパー関数（_kabusys.ai.*._call_openai_api）を unittest.mock.patch で差し替え可能にしている。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT や ON CONFLICT を想定）して、再実行や部分失敗に対して既存データを保護する。
- 環境変数に関する注意:
  - 必須環境変数取得時は _require が ValueError を投げる（ユーザに .env.example を参照させるメッセージ付き）。
  - .env の読み込み/上書き動作は OS 環境変数を上書きしない安全なデフォルトを採用（.env.local は上書き可）。

Security
- 機密情報（OpenAI API キーなど）は Settings で必須チェックとし、明示的に渡すか環境変数から取得するよう設計。自動 .env 読み込みは明示的に無効化できる。

今後の予定（例）
- ai モジュールの LLM プロンプト/モデルのチューニング。
- ETL の品質チェックルール拡充。
- calendar_update_job の API フェイルオーバーやリトライ戦略の改善。
- research 側での追加ファクター・バックテストインターフェースの追加。

--- 

（注）本 CHANGELOG は提示されたソースコードから仕様・実装挙動を推測して作成しています。実際のコミット履歴や変更履歴と差異がある可能性があります。
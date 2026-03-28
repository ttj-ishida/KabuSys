# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を導入。
  - 主要サブパッケージを公開: `data`, `strategy`, `execution`, `monitoring`（`__all__` 経由）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。読み込み優先順は OS 環境変数 > `.env.local` > `.env`。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途向け）。
  - プロジェクトルートの探索は `__file__` を基点に `.git` または `pyproject.toml` を検出して行うため、CWD に依存しない。
  - .env のパースは以下をサポート/考慮:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの値で `#` をインラインコメントとして認識する場合の挙動（直前が空白／タブの場合のみコメント扱い）。
  - 必須環境変数を取得するヘルパー `_require()` を提供（未設定時は ValueError を送出）。
  - 設定ラッパー `Settings` を提供し、以下のキー取得用プロパティを実装:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト: data/kabusys.duckdb）、`sqlite_path`（data/monitoring.db）
    - システム: `env`（`development`/`paper_trading`/`live` の検証）、`log_level`（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` の検証）、`is_live`/`is_paper`/`is_dev` ヘルパー

- AI（NLP）モジュール
  - `kabusys.ai.news_nlp`:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得する `score_news(conn, target_date, api_key=None)` を実装。
    - ニュースウィンドウ計算（JST 前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う）を `calc_news_window` で提供。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄、1銘柄あたりの記事上限 _MAX_ARTICLES_PER_STOCK=10、文字数上限 _MAX_CHARS_PER_STOCK=3000。
    - JSON mode を利用した堅牢なレスポンス検証 `_validate_and_extract` を実装。部分失敗時も他銘柄の既存スコアを保護するために、DB への置換は対象コードのみを DELETE → INSERT。
    - API 呼び出し失敗時は指数バックオフでリトライ（429、ネットワーク断、タイムアウト、5xx を対象）。
    - テストのために `_call_openai_api` を patch で差し替え可能（unittest.mock.patch 推奨）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（`bull`/`neutral`/`bear`）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - MA 計算はルックアヘッドバイアス回避のため target_date 未満のデータのみを使用。データ不足時は中立 (ma200_ratio = 1.0) を採用。
    - マクロニュース抽出はキーワードベース（`_MACRO_KEYWORDS`）で最大 `_MAX_MACRO_ARTICLES` 件を取得。
    - OpenAI 呼び出しは専用実装で行い、API 失敗時は `macro_sentiment=0.0` としてフォールバック（フェイルセーフ）。
    - 得られたスコアは閾値によりラベリングし、`market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - モデル: `_MODEL = "gpt-4o-mini"`、リトライ設計あり。

- リサーチ（因子・特徴量探索）モジュール (`kabusys.research`)
  - ファクター計算:
    - `calc_momentum(conn, target_date)`：1M/3M/6M リターン、200 日 MA 乖離率（不足時は None）。
    - `calc_volatility(conn, target_date)`：20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - `calc_value(conn, target_date)`：PER（EPS が 0 または欠損なら None）、ROE（最新の財務データを参照）。
  - 特徴量探索ユーティリティ:
    - `calc_forward_returns(conn, target_date, horizons=None)`：デフォルト horizons=[1,5,21]、複数ホライズンを一度に取得。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`：Spearman ランク相関（IC）計算。十分なサンプルが無ければ None。
    - `rank(values)`：同順位は平均ランクで処理（丸め誤差対策で round を使用）。
    - `factor_summary(records, columns)`：count/mean/std/min/max/median を算出。
  - すべて DuckDB 上の `prices_daily` / `raw_financials` 等を参照し、外部 API に依存しない実装。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装。J-Quants クライアント経由で差分取得し、`market_calendar` テーブルへ冪等保存。
    - 営業日判定・検索ユーティリティ: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を実装。DB 登録値を優先し、未登録日は曜日ベースでフォールバック。
    - バックフィル（直近 `_BACKFILL_DAYS` 日は再取得）や最大探索範囲 `_MAX_SEARCH_DAYS` による安全措置を導入。
    - 異常検知（last_date が過度に将来の場合はスキップ）などの健全性チェックを実装。
  - ETL / パイプライン (`pipeline`, `etl`):
    - ETL 実行結果を表す `ETLResult` dataclass を導入（取得件数・保存件数・品質問題・エラー一覧を保持）。
    - 差分更新・バックフィル方針、品質チェック（`kabusys.data.quality`）との連携方針を実装。品質チェックは収集のみ行い、呼び出し元で対処を決定（Fail-Fast ではない）。
    - DB テーブル存在確認、最大日付取得ユーティリティなどを提供。

### 注意 / ドキュメント
- OpenAI API
  - `score_news` / `score_regime` は OpenAI API キーを必要とします。引数 `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。未設定の場合は ValueError を送出します。
  - 使用モデルは現状 `gpt-4o-mini` を想定しています（定数 `_MODEL`）。
- テスト性
  - AI モジュール内の `_call_openai_api` はテスト時に patch して差し替え可能（テスト用のフックを明示）。
  - 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化でき、テスト時にプロセス環境を維持しやすくしています。
- DB（DuckDB）
  - DuckDB への依存が強いため、実行環境に DuckDB を用意してください。
  - 一部 DuckDB バージョン依存（例: executemany に空リストを渡せない等）の対応がソース内コメントにあります。

### 既知の制約 / TODO（初期実装）
- パフォーマンスチューニングや大規模データでのベンチは今後の課題。
- 一部ファクター（PBR・配当利回り）は未実装（calc_value の注記参照）。
- OpenAI 呼び出しの詳細（レート・コスト管理）は運用ルールに依存するため別途運用ガイドを推奨。
- `strategy`, `execution`, `monitoring` パッケージの実装は公開済みだが、今回のリリースでは主要焦点をデータ・研究・NLP に置いている。

---

以上が v0.1.0 の主な追加点と注意事項です。今後のリリースではバグ修正・API 拡張・運用性改善（監査ログ、メトリクス、リトライ政策の詳細化 等）を予定しています。
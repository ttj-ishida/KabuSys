# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- 初期リリース。パッケージ名: `kabusys`。パッケージバージョンは `0.1.0` に設定。
- パッケージ公開インターフェース:
  - `__all__ = ["data", "strategy", "execution", "monitoring"]`

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルートの自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env のパースを強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無の差異を考慮）
  - 自動ロードの優先順位: OS 環境変数 > `.env.local` > `.env`
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
  - 環境変数の保護（OS 環境変数を protected として上書き防止）
  - `Settings` クラスを提供し、主要設定をプロパティとして取得可能:
    - J-Quants / kabuStation / Slack / DB パス等の取得 (`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `duckdb_path`, `sqlite_path` 等)
    - `env`、`log_level` の値検証（許容値チェック）
    - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティ
  - 必須環境変数未設定時は明示的に `ValueError` を投げる設計（ユーザーに分かりやすいエラーメッセージ）。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行う。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理（チャンク化）。
    - タイムウィンドウ: JST 基準で「前日 15:00 〜 当日 08:30」（UTC では前日 06:00 〜 23:30）を使用。window 計算ユーティリティ `calc_news_window` を提供。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、`results` キー・型チェック、未知コードの無視、スコアの ±1.0 クリップ。
    - 取得スコアは `ai_scores` テーブルへ冪等的に書き込み（DELETE -> INSERT、部分失敗時に既存データを保護）。
    - テスト用に OpenAI API 呼び出し関数を差し替え可能（`_call_openai_api` を patch で置換）。
    - 処理結果は書き込み件数（銘柄数）を返す。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（`bull`/`neutral`/`bear`）。
    - マクロキーワードで raw_news をフィルタし、最大 20 記事を LLM に渡してセンチメントを算出。
    - LLM モデルは gpt-4o-mini、JSON モードで `{"macro_sentiment": ...}` を期待。
    - フェイルセーフ: API 呼び出し失敗時は `macro_sentiment = 0.0` として継続。
    - リトライポリシー: 最大 3 回（指数バックオフ）で再試行。5xx とネットワーク系に対してリトライ。
    - レジームスコア合成とクリップ処理、閾値に基づくラベル決定（パラメータ化された閾値と重み）。
    - `market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックを試み例外を上位へ伝播。
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定。未指定時は `ValueError`。

- データプラットフォーム関連 (`kabusys.data`)
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの取得・夜間バッチ更新ジョブ (`calendar_update_job`) を実装（J-Quants クライアント経由）。
    - カレンダー存在チェックに基づくフォールバック（DB 未取得時は曜日ベースで土日非営業日扱い）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - 最大探索範囲を設定して無限ループを防止（`_MAX_SEARCH_DAYS`）。
    - バックフィル期間や先読み期間をパラメータ化（`_BACKFILL_DAYS`, `_CALENDAR_LOOKAHEAD_DAYS`）。
    - calendar_update_job は健全性チェック（将来日付の異常検出）を実施し、J-Quants API 例外発生時は安全に 0 を返す。

  - ETL パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL の公開結果型 `ETLResult` を実装（dataclass）。価格・財務・カレンダーの取得/保存件数、品質問題、エラーを集約。
    - 差分取得、バックフィル、品質チェック（`kabusys.data.quality` を想定）設計に基づく構成。
    - `_get_max_date` 等の DB ユーティリティを実装して差分計算を補助。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

  - J-Quants クライアントインターフェース（参照実装として `kabusys.data.jquants_client` を想定して依存）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群を実装:
    - `calc_momentum`: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - `calc_volatility`: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - `calc_value`: PER（EPS が 0 または欠損時は None）、ROE（raw_financials の最新値を使用）。
  - 特徴量探索ユーティリティ (`kabusys.research.feature_exploration`):
    - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（存在しない場合は None）。
    - `calc_ic`: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効サンプルが 3 未満の場合は None。
    - `rank`: 同順位は平均ランクで処理（丸め対策あり）。
    - `factor_summary`: カラムごとの count/mean/std/min/max/median を計算。
  - いずれの関数も DuckDB 接続を受け取り、DB 内のテーブル（主に `prices_daily`, `raw_financials`）のみを参照。外部 API にはアクセスしない設計。

### 改善 (Changed)
- 設計方針や実装上の注意点をパイプライン全体で統一：
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計（すべての関数は target_date を引数で受け取る）。
  - DB への書き込みは冪等化（削除→挿入、ON CONFLICT 相当）を基本とし、部分失敗時に既存データを保護する実装。
  - OpenAI 呼び出しは各モジュールで独立した内部ラッパーを持ち、テスト時に差し替えやすくしている（モジュール結合を避ける）。

### 修正 (Fixed)
- 安全性・堅牢性の向上:
  - OpenAI レスポンスや JSON パース失敗時に例外を投げずフェイルセーフ（0.0 にフォールバック）で継続する箇所を明示。
  - API エラーのステータスコード有無に対応するため `getattr(..., "status_code", 500)` を利用。
  - DuckDB の executemany が空リストを受け付けない挙動を考慮して空チェックを追加。

### 既知の制約・注意点 (Notes)
- OpenAI API の利用:
  - news_nlp/regime_detector は OpenAI（gpt-4o-mini）を利用。実行には `OPENAI_API_KEY`（または関数引数）が必要。
  - API 呼び出しは JSON モードを期待するため、モデル挙動に依存する点に注意。
- 環境変数:
  - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等、いくつかの値は必須（未設定時はエラー）。
- DB スキーマ依存:
  - 多くの処理は DuckDB の特定テーブル（`prices_daily`, `raw_news`, `news_symbols`, `ai_scores`, `market_regime`, `raw_financials`, `market_calendar` 等）を前提としている。適切なスキーマ / 初期ロードが必要。
- 不足データ時の挙動:
  - 移動平均等でデータ不足の銘柄は None を返すか、レジーム計算等では中立値（1.0 や 0.0）を利用するなどのフェイルセーフが適用される。
- テスト支援:
  - OpenAI 呼び出しラッパーを unittest.mock.patch で差し替え可能にしており、API を実際に叩かずにユニットテストが可能。

---

今後のリリースでは以下を検討してください（例）:
- docs、使用例（Quickstart）、DB スキーマ定義・マイグレーション用スクリプトの追加
- 単体テスト・統合テストのサンプルと CI 設定
- キャッシュや並列化による処理性能改善
- OpenAI モデル指定やプロンプトの外部化（設定化）による柔軟化

---
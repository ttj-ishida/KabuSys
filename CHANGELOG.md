# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 本CHANGELOGはコードベースの内容から推測して作成しています。実装上の意図や設計方針、公開 API の振る舞い等も合わせて記載しています。

## [Unreleased]

なし

## [0.1.0] - 2026-04-04

初回公開リリース（初期実装）。以下の機能群とユーティリティを提供します。

### 追加 (Added)

- パッケージ基本
  - パッケージ名: `kabusys`、バージョン `0.1.0` を設定。
  - パッケージの公開モジュール: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装（優先順: OS 環境 > .env.local > .env）。
  - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパースは以下をサポート:
    - コメント行・空行の無視
    - `export KEY=val` 形式
    - シングル/ダブルクォート付き値（バックスラッシュエスケープ対応）
    - クォート無し値のインラインコメント取り扱い（直前が空白またはタブの場合）
  - `.env` 読み込み時の上書き制御（override / protected キー保護）を実装。
  - 必須環境変数取得用ヘルパ `_require`（未設定時は ValueError を送出）。
  - Settings クラスを公開 (`settings`)。以下の設定プロパティを提供:
    - J-Quants / kabu ステーション / LINE 等の API トークン
    - DB ファイルパス（duckdb / sqlite）
    - 監視 PID/kill フラグパス、クリア挙動フラグ
    - CPU/Memory/Disk しきい値（パーセンテージ）
    - 環境 (`KABUSYS_ENV`) 値検証（`development` / `paper_trading` / `live`）
    - `LOG_LEVEL` の検証（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
    - is_live / is_paper / is_dev のヘルパ

- AI モジュール: ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを取得。
  - 時間ウィンドウ: JST 基準で「前日 15:00 ～ 当日 08:30」を対象（calc_news_window を提供）。
  - 銘柄ごとに最新記事を最大件数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 一度に最大 20 銘柄単位でバッチ送信（チャンク処理）。
  - API 呼び出しの堅牢化:
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - リトライ上限到達や致命的エラー時は該当チャンクをスキップ（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をモック可能に実装。
  - レスポンスのバリデーションとスコアクリップ（±1.0）。
  - 書き込みはトランザクションで ai_scores テーブルへ（部分成功時に既存スコアを保護するため対象コードで DELETE → INSERT）。
  - 空結果やスキップ時のログ出力を実装。
  - `score_news(conn, target_date, api_key=None)` を公開。戻り値は書き込んだ銘柄数。

- AI モジュール: 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（'bull' / 'neutral' / 'bear'）。
  - ma200 乖離の計算はルックアヘッドバイアス防止のため target_date 未満のデータのみ使用。
  - マクロニュースは raw_news からキーワードで抽出（キーワードリスト実装）。
  - OpenAI 呼び出し（gpt-4o-mini, JSON mode）に対するリトライと 5xx の取り扱いを実装。API 失敗時は macro_sentiment=0.0 にフォールバックして継続。
  - スコア合成後に market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。`score_regime(conn, target_date, api_key=None)` を公開。
  - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError。

- データ基盤関連 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダーを扱うための CRUD および判定ユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar の存在有無に応じた曜日ベースのフォールバック（DB 登録ありは DB 値優先）。
    - カレンダー夜間更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants クライアント呼び出し、バックフィル、健全性チェック）。
    - 探索の最大日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
  - ETL パイプライン (`pipeline` と `etl`):
    - ETL 実行結果を表す dataclass `ETLResult` を実装（取得数、保存数、品質チェック結果、エラー一覧等を含む）。
    - ETL の設計方針として差分取得、バックフィル挙動（デフォルト backfill 3 日）、品質チェックの収集型処理を採用。
    - `etl` モジュールは pipeline の `ETLResult` を再エクスポート。
    - DuckDB を用いたテーブル存在チェックや最大日付取得ユーティリティを実装（ETL の下地）。

- リサーチ（研究）モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`):
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0 または欠損なら PER は None）。
    - DuckDB のウィンドウ関数を活用して効率的に集計。
    - 全関数は prices_daily / raw_financials のみ参照し外部 API へアクセスしない設計。
  - 特徴量探索 (`research.feature_exploration`):
    - calc_forward_returns: デフォルトホライズン [1,5,21] の将来リターンを計算。horizons のバリデーションを実施。
    - calc_ic: Spearman ランク相関（情報係数）を実装。有効レコードが 3 件未満の場合は None を返す。
    - rank: 同順位は平均ランクで扱う実装（比較前に round(..., 12) を適用して浮動小数点誤差を緩和）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
    - 標準ライブラリのみで実装（pandas 等外部依存を回避）。

- テスト支援 / 実装上の配慮
  - OpenAI 呼び出し部分はテストで差し替え可能（_call_openai_api を patch できるように実装）。
  - ルックアヘッドバイアスを避けるため、date 型の引数を受け内部で datetime.today() / date.today() を参照しない設計を各モジュールで採用。
  - DuckDB の executemany に関する互換性問題（空リスト禁止）に配慮した実装。

### 変更 (Changed)

- (初期リリースのため該当なし)

### 修正 (Fixed)

- (初期リリースのため該当なし)

### 廃止 (Deprecated)

- なし

### 削除 (Removed)

- なし

### セキュリティ (Security)

- OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から明示的に渡す必要があり、未設定時は ValueError により処理を停止してキー漏洩等の誤動作を避ける設計。
- .env 自動読み込みは明示的に無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。

---

備考:
- 本リリースはコード上の実装と設計方針からまとめた初期 CHANGELOG です。実際の利用時には運用上の注意点（API 利用料、レート制限、秘密情報の管理、DB スキーマ整備など）を別途ドキュメント化してください。
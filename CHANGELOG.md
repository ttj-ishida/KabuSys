# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このリポジトリの初版リリースを記録しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システムの基盤機能を実装しました。
主な追加点・設計方針・既知の制約を以下にまとめます。

### Added
- 全体
  - パッケージ `kabusys` を公開（バージョン 0.1.0）。
  - モジュール構成: data, research, ai, config, 他ユーティリティ群を実装。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数からの設定読み込みを自動で行う仕組みを実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト向け）。
  - .env パーサを実装（コメント、`export KEY=val` 形式対応、シングル／ダブルクォート内のエスケープ処理対応、インラインコメントの扱い）。
  - 環境変数必須チェック用 `_require()` と、アプリケーション設定ラッパ `Settings` を提供。
    - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（利用時）など。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効値の制限）を実装。
  - デフォルトの DB パス（DuckDB / SQLite）設定を提供。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - 関数 `score_news(conn, target_date, api_key=None)` を実装。
    - 前日15:00 JST〜当日08:30 JST のニュースを対象に、銘柄別に記事を集約して LLM（gpt-4o-mini）へバッチ送信し、センチメントスコアを `ai_scores` テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/呼び出し）、1銘柄当たりの最大記事数／文字数トリム、レスポンスの厳格な検証とスコアの ±1.0 クリップを実装。
    - 429・ネットワーク・タイムアウト・5xx に対するエクスポネンシャルバックオフ（リトライ）を実装。致命的でない失敗はフェイルセーフでスキップ。
    - OpenAI 呼び出しはテスト時に差し替え可能（private 関数を patch 可能）。
    - DuckDB の互換性（executemany の空リスト不可等）に配慮して書込み処理を実装。
    - `calc_news_window(target_date)` で対象ウィンドウ（UTC naive datetime）を計算。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - 関数 `score_regime(conn, target_date, api_key=None)` を実装。
    - ETF 1321 の直近 200 日終値から MA200 乖離率を計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードでフィルタしたニュースタイトルを LLM に投げてマクロセンチメントを評価（記事がない場合は LLM 呼び出しをスキップし 0.0 とする）。
    - MA（70%）とマクロ（30%）を重み付けしてレジームスコアを合成し、`market_regime` テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しに対するリトライ・エラー処理（APIError の status_code 取り扱い等）とフェイルセーフを実装。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - `calc_momentum(conn, target_date)`: mom_1m/mom_3m/mom_6m、ma200_dev（データ不足時は None）を計算。
    - `calc_volatility(conn, target_date)`: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - `calc_value(conn, target_date)`: EPS / PER、ROE を raw_financials と prices_daily から計算（EPS 0/欠損は None）。
    - DuckDB 上で SQL ウィンドウ関数を多用し高速に集計する設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - `calc_forward_returns(conn, target_date, horizons=None)`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`: スピアマンランク相関（IC）を計算。
    - `rank(values)`: 平均順位でのランク付け（同順位は平均ランク）。
    - `factor_summary(records, columns)`: count/mean/std/min/max/median の統計サマリを返す。
    - すべて標準ライブラリ＋DuckDB のみで実装（pandas 等外部依存なし）。

- Data（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants API 経由）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。
    - market_calendar が未取得のときの曜日ベースフォールバック、DB の値優先の一貫した振る舞い、最大探索日数制限などを実装。
    - API 取得 → 保存までの冪等処理（jquants_client 経由）を想定。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表す dataclass `ETLResult` を実装（品質チェック結果やエラーの集約、辞書化機能を提供）。
    - 差分取得、バックフィル、品質チェック統合のためのユーティリティを用意（jquants_client, quality モジュールとの連携を想定）。
    - 一部ヘルパー（テーブル存在チェック、最大日付取得など）を実装。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

### Fixed
- 初期版につき「修正」は該当なし。ただし以下の堅牢性改善を含む:
  - .env パーサでクォート内のエスケープや export 形式、インラインコメントを正しく扱うように実装。
  - OpenAI 呼び出し時の各種例外（RateLimitError、APIConnectionError、APITimeoutError、APIError）を細かく扱い、適切にリトライ／フォールバックするように実装。
  - DuckDB に対する互換性問題（executemany に空リストを渡さない等）に対応。

### Security
- 機密情報（API キー等）は環境変数で管理する設計。自動ロード機能は存在するが、テスト等で無効化するための環境変数を用意（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Known issues / Limitations
- raw_financials に基づく PBR や配当利回り等の指標は現バージョンで未実装（calc_value の注記参照）。
- OpenAI の利用は外部 API に依存するため、API 料金・利用制限が発生する。API キーは `OPENAI_API_KEY` 環境変数、または各関数の api_key 引数で注入する必要あり。
- jquants_client / quality 等の外部連携モジュールは本コード内で参照しているが、外部実装の存在を前提としている。
- ルックアヘッドバイアス回避のため、データ取得・計算で datetime.today()/date.today() を関数内で参照しない設計を採用。ETL/スコアリングは明示的な target_date を引数として与える必要があります。
- 一部ユーティリティは DuckDB の返却型やバージョン差に依存するため、実行環境の DuckDB バージョンにより挙動が変わる可能性あり。

### Notes / Testing hooks
- OpenAI 呼び出し関数（各モジュールの `_call_openai_api`）や `_score_macro` の `_sleep_fn` などはテストで差し替え可能（unittest.mock.patch を想定）。
- DuckDB を用いる関数はすべて接続オブジェクト（conn）を受け取り、外部依存を注入可能にしてあるため単体テストが容易。

---

（今後のリリースではバグ修正・追加機能・API 変更点をここに時系列で追記します。）
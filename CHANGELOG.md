# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従っています。

現在のバージョンはパッケージの __version__ に準拠しています。

## [Unreleased]

- 次版の変更点をここに記載します。

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)

- パッケージ構成
  - 基本パッケージエントリポイント `kabusys`（__version__ = 0.1.0）。主要サブパッケージとして `data`, `research`, `ai`, `execution`, `monitoring`, `strategy` をエクスポート対象に設定。

- 設定管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込む機能を実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサはコメント、export プレフィックス、シングル／ダブルクォート、エスケープシーケンスに対応。
    - `Settings` クラスを提供し、主要設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等）をプロパティ経由で取得。未設定の必須環境変数は ValueError を送出する。

- AI（LLM）関連
  - `kabusys.ai.news_nlp` を追加。
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを計算。
    - 時間ウィンドウは JST ベースで前日15:00〜当日08:30（内部は UTC naive に変換）を採用。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数制限、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - テスト用に `_call_openai_api` をパッチ可能（unittest.mock.patch）に実装。
    - 公開関数: `score_news(conn, target_date, api_key: Optional[str])` — ai_scores テーブルへ書き込み。

  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）判定を行う。
    - マクロニュース抽出のキーワードセット実装、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力を期待。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開関数: `score_regime(conn, target_date, api_key: Optional[str])` — market_regime テーブルへ書き込み。

- Data（ETL / カレンダー）
  - `kabusys.data.pipeline` を追加。
    - 差分取得、バックフィル、品質チェックの呼び口となる ETL のインターフェースを定義。
    - ETL 実行結果を表す `ETLResult` dataclass を実装（to_dict、エラーフラグ等を含む）。
  - `kabusys.data.calendar_management` を追加。
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - JPX カレンダーを J-Quants API から取得して更新する `calendar_update_job` を実装（バックフィル・健全性チェック付き）。
    - DB 未取得時は曜日ベース（土日休み）でフォールバックする堅牢な設計。
  - `kabusys.data.etl` は pipeline の ETLResult を再エクスポート。

- Research（ファクター・特徴量解析）
  - `kabusys.research.factor_research` を追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR）、Value（PER・ROE）等の計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を多用して効率的に集計。
    - 公開関数: `calc_momentum`, `calc_volatility`, `calc_value`（いずれも conn, target_date を引数）。
  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと duckdb のみで実装。
  - `kabusys.research.__init__` で主要関数を再エクスポート。

- ユーティリティ・ロギング設計
  - 各モジュールで詳細なログ出力を追加（info/debug/warning/exception）。
  - 外部 API 呼び出しの失敗は基本的にフェイルセーフで継続する設計（ただし DB 書き込み失敗は例外伝播）。

### 変更 (Changed)

- （初回リリースのため対象なし）

### 修正 (Fixed)

- （初回リリースのため対象なし）

### 既知の制約・設計ノート (Notes)

- OpenAI クライアントは gpt-4o-mini を前提に JSON Mode（response_format={"type": "json_object"}）で使用する設計になっている。API レスポンスが期待した JSON 形式でない場合はログに WARNING を出力してスキップし、部分的に結果を保存する実装になっている。
- 日付処理はルックアヘッドバイアスを避けるため、各関数で明示的な target_date 引数を受け取り、内部で datetime.today() / date.today() を直接参照しない方針を採用している（ただし calendar_update_job はバッチのため date.today() を使用）。
- DuckDB のバージョン差分に起因するバインドの制約（executemany の空リスト不可や list バインドの不安定さ等）に配慮した実装を行っている。
- .env の自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。プロジェクト配布後は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して自動読み込みを無効化することを推奨。
- テスト容易性のため、OpenAI API 呼び出し箇所は関数単位でパッチ可能に実装されている（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- セキュリティ: 必須のシークレット系環境変数が未設定の場合は ValueError を送出して明示的に失敗する。

---

この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして公開する際は、コミット履歴やリリース作業時のメモを元に必要に応じて調整してください。
# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。Semantic Versioning を想定します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを初期リリース。バージョンは `0.1.0`。
  - パッケージの公開 API を整理（`__all__` に data, strategy, execution, monitoring 等を定義）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して .env を読み込む（CWD 非依存）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサは以下に対応：
    - 空行 / コメント行 / `export KEY=val` 形式。
    - シングル・ダブルクォートとバックスラッシュエスケープの適切な扱い。
    - クォート無しの行でのインラインコメント処理（`#` の前がスペース/タブの場合のみコメントとみなす）。
  - 既存 OS 環境変数を保護するための protected keys 機能と override オプション。
  - 必須項目取得用 `_require()` 実装（未設定時は ValueError）。
  - Settings クラスを提供（プロパティ経由で設定を取得）。
    - J-Quants / kabu ステーション / Slack / DB パスなどの設定を提供。
    - `KABUSYS_ENV`（development / paper_trading / live）と `LOG_LEVEL` の値検証。
    - `duckdb_path` / `sqlite_path` のデフォルトパスと Path 変換。

- データ層（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの運用ロジック（market_calendar の読み書き、フォールバック）を実装。
    - 営業日判定 API: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`。
    - DB 登録がない場合の曜日ベースのフォールバックを含む一貫した挙動。
    - 夜間バッチ処理 `calendar_update_job` 実装（J-Quants から差分取得、バックフィル、健全性チェック）。
  - ETL / パイプライン（pipeline）
    - 差分更新、保存、品質チェックの流れを想定した ETLResult データクラスを実装。
    - DuckDB と組み合わせた最大日付取得やテーブル存在チェック等のユーティリティを提供。
    - jquants_client との連携想定（差分フェッチ → save_* で Idempotent 保存）。
    - 品質チェック結果（quality.QualityIssue）を ETLResult に格納し、エラー判定用プロパティを提供。
  - ETLResult を再エクスポートする etl モジュールを追加。

- 研究（research）
  - factor_research
    - モメンタム / ボラティリティ / バリュー系ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None / 警告）。
      - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
      - calc_value: PER, ROE（raw_financials から最新財務を取得して計算）。
    - DuckDB を用いた SQL ベースの実装（外部 API への依存なし）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効データ不足時は None）。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸めで ties を安定化）。
    - factor_summary: カラム別の count/mean/std/min/max/median を算出。
  - research パッケージのエクスポートを整理。

- AI / NLP 機能（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を参照し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - ニュース収集ウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）。
    - バッチ送信（最大 20 銘柄/回）・トークン肥大化対策（記事数上限・文字数上限）。
    - JSON mode を用いた応答パースとバリデーション（results 配列の検証、未知コードの無視、数値検証）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。
    - トランザクション単位で ai_scores を置換（DELETE → INSERT、部分失敗時に既存データ保護）。
    - テストしやすさのため OpenAI API 呼び出し部分は差し替え可能（内部関数をモック可能）。
  - regime_detector
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（OpenAI、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window と raw_news から抽出して LLM 評価。
    - LLM 呼び出しは独立実装（モジュール間結合の回避）。
    - API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- 汎用・設計上の注意点
  - "look-ahead bias" 対策: 各種処理で datetime.today()/date.today() を直接参照しない設計（ターゲット日を引数で与える形式）。
  - DuckDB を中心とした SQL 主導のデータ処理で、外部発注 API 等へのアクセスはなし（研究・分析と実運用を分離）。
  - ロギングを多用し、API 失敗 / データ不足等が起きた際のフォールバック動作を明示。
  - OpenAI API キーは引数注入または環境変数 `OPENAI_API_KEY` で解決（テスト容易化のための注入をサポート）。
  - トランザクション処理と部分失敗時の保護（例: 書き込み対象を絞ることで既存データを守る）。

### 変更 (Changed)
- （新規リリースのため該当なし）

### 修正 (Fixed)
- （新規リリースのため該当なし）

### 削除 (Removed)
- （新規リリースのため該当なし）

### セキュリティ (Security)
- 環境変数に機密情報（OpenAI API キー、SLACK_BOT_TOKEN、KABU_API_PASSWORD、JQUANTS_REFRESH_TOKEN 等）を想定。これらは必須取得ロジックで未設定時に例外を投げる実装があるため、運用時は .env または安全なシークレット管理を利用すること。

---

注: 上記はソースコードから推測してまとめた変更履歴です。実際のリリースノートやパッケージ公開時は、リリース日や変更点の正式確定を反映してください。
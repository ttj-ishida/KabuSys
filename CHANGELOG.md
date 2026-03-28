# Changelog

すべての重要な変更は Keep a Changelog の準拠に従って記載します。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-28

### Added
- パッケージの初期公開
  - pakage: kabusys （__version__ = 0.1.0）
  - 公開サブパッケージの意図的なエクスポート: data, strategy, execution, monitoring

- 環境設定管理 (`kabusys.config`)
  - .env ファイル（.env と .env.local）または OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト用）。
  - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を基準に探索（CWD 非依存）。
  - 柔軟な .env パーサ実装:
    - コメント／空行無視、`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォート無しのインラインコメント処理（`#` 前が空白/タブの場合にコメント扱い）。
  - .env 読み込みの上書き制御（override）と OS 環境変数の保護（protected set）。
  - Settings クラスでアプリ設定をプロパティとして提供（必須項目は _require で検証）。
    - J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live） / ログレベル 等を取得。
    - 不正な env 値に対する明示的なエラー検出。

- AI 関連（kabusys.ai）
  - news_nlp モジュール（`score_news`）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメント評価を行い `ai_scores` テーブルへ書き込み。
    - タイムウィンドウ定義（JST: 前日15:00～当日08:30 → UTC に変換して DB 検索）。
    - バッチ処理実装（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの記事数/文字数上限でプロンプト肥大化対策。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、`results` リスト、コード一致、数値チェック）とスコアの ±1.0 クリップ。
    - 部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT で置換する冪等書き込み。
    - エラーは基本的にフェイルセーフ（API 失敗時はスキップして継続）。テスト用に API 呼び出しをモック可能。

  - regime_detector モジュール（`score_regime`）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロ記事を取得。OpenAI（gpt-4o-mini）を用いてマクロセンチメントを JSON で評価。
    - API 呼び出しのリトライ（RateLimit/ネットワーク/5xx に対する再試行）とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成とクリップ、ラベル付与後に market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - ルックアヘッドバイアス回避のため、target_date 未満のデータのみを利用。

- データ基盤（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）を使った営業日判定ヘルパー群:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でのフォールバック。
    - next/prev は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
    - 最大探索日数やバックフィル、先読み日数などの定数管理。

  - pipeline / etl モジュール
    - ETLResult データクラスを公開（ETL の実行結果集約）。
    - ETL 設計（差分取得、品質チェック、idempotent 保存、バックフィル）に沿ったユーティリティ群の実装方針を反映。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。

- 研究用モジュール（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 偏差）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily/raw_financials を用いて計算。
    - データ不足時の None 処理、結果を辞書リストで返す設計。
    - SQL のウィンドウ関数を活用した効率的実装とログ出力。

  - feature_exploration モジュール
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を持たず（pandas など未使用）、標準ライブラリと DuckDB のみで完結。
    - 入力検証（horizons の範囲チェック、最小サンプル数チェック）を実装。

### Changed
- （初期リリース）設計方針・実装で以下を一貫して採用
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を主処理で参照しない（target_date 指定に基づく設計）。
  - DuckDB をデータ処理の中心に採用。
  - OpenAI 連携は gpt-4o-mini + JSON mode を使用し、レスポンスの堅牢な検証を行う。
  - API 呼び出しに対する再試行（指数バックオフ）とフェイルセーフの扱いを明確化。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を確保。

### Fixed
- 該当なし（初期リリース） — 実装には多くのログ出力と例外ハンドリングが含まれ、障害時の挙動が明示されている。

### Security
- 環境変数の読み込み時に OS 環境変数の上書きを保護する仕組みを導入（protected set）。
- OpenAI API キーは明示的に引数で注入可能。未設定時は ValueError を送出して誤った動作を防止。

### Notes
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API は news_nlp/regime_detector で必要（OPENAI_API_KEY 環境変数または関数引数）
- DB ストレージ既定
  - DuckDB: data/kabusys.duckdb（設定で変更可能）
  - SQLite（monitoring 用）: data/monitoring.db（設定で変更可能）
- OpenAI 関連のテスト容易性
  - 各モジュールの内部 API 呼び出し関数（_call_openai_api 等）はユニットテストで patch しやすい実装になっている。

---

今後のリリースでは、strategy / execution / monitoring の具体的実装、追加のデータ品質チェック、より詳細なドキュメントやサンプル ETL 実行例を追加する予定です。必要であれば、この CHANGELOG を英語版やより細分化した履歴（Unreleased / 次バージョンの計画等）に拡張します。
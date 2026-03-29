# CHANGELOG

すべての変更は「Keep a Changelog」フォーマットに準拠します。日付はリリース作成日（このドキュメント作成時）です。

## [Unreleased]

- （現在未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システムの基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加（Added）

- パッケージ基盤
  - パッケージ名: `kabusys`（__version__ = 0.1.0）
  - パッケージ公開用の __all__ を設定（data, strategy, execution, monitoring を想定）

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（および .env.local）や環境変数から設定を自動読み込みするユーティリティを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探索して自動ロード（CWD に依存しない）。
  - .env パーサーは以下に対応：
    - コメント行・空行の無視、`export KEY=val` 形式のサポート
    - クォート（シングル／ダブル）内のバックスラッシュエスケープ処理
    - クォートなしの場合はインラインコメントの取り扱い（前が空白またはタブの '#' をコメントとして扱う）
  - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意（テスト用）。
  - 現在の設定を取得する `Settings` クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
  - 必須環境変数未設定時は ValueError を送出する `_require` 実装。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news + news_symbols から銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを評価、結果を ai_scores テーブルへ書き込む。
    - バッチ処理（1 API コールで最大 20 銘柄）・トークン肥大化対策（記事数・文字数トリム）・JSON モード利用。
    - リトライロジック（429、接続断、タイムアウト、5xx を対象に指数バックオフ）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ。
    - DuckDB の executemany に空リストを渡せない制約への対応（書き込み前に空チェック）。
    - テスト容易性のため OpenAI 呼び出し関数（_call_openai_api）を patch 可能。
    - タイムウィンドウは JST ベースで定義され、DB 比較は UTC naive datetime を使用（ルックアヘッド防止のため date.today() を参照しない設計）。

  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、calc_news_window 経由でニュースウィンドウを決定。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（最大記事数制限、リトライ、フェイルセーフで macro_sentiment=0.0 にフォールバック）。
    - スコア合成・閾値判定後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは news_nlp と別実装とし、モジュール結合を避ける設計。

- データ（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）と運用ヘルパーを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar データがない場合は曜日ベースのフォールバック（週末除外）。
    - DB にある日付は DB 値を優先し、未登録日は曜日フォールバックで一貫した振る舞いを提供。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル、健全性チェックを実装。

  - pipeline / etl モジュール
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧など）。
    - 差分更新・バックフィル方針・品質チェック（quality モジュール連携）の設計に基づく ETL 基盤。
    - ETLResult の to_dict により品質問題をシリアライズ可能。
    - data.etl は pipeline.ETLResult を再エクスポート。

- 研究（kabusys.research）
  - factor_research モジュール
    - Momentum、Value、Volatility（ATR）等の定量ファクター計算を実装。
    - DuckDB の SQL + Python で計算を行い、prices_daily / raw_financials のみ参照（発注 API 等にはアクセスしない）。
    - calc_momentum / calc_volatility / calc_value を提供（結果は (date, code) をキーとする dict のリスト）。
    - 実装はデータ不足時に None を返すなど堅牢化。

  - feature_exploration モジュール
    - calc_forward_returns（将来リターン）、calc_ic（スピアマンランク相関による IC）、factor_summary、rank 等の統計ユーティリティを実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装。
    - rank は同順位を平均順位で処理し、丸め誤差対策のため round(..., 12) を利用。

### 修正（Changed）

- -（初版のため過去変更は無し）

### 修正（Fixed）

- -（初版のため修正履歴は無し）

### セキュリティ（Security）

- OpenAI API キーとその他必須トークンは環境変数から読み込む設計。未設定時は明確に ValueError を発生させることで誤動作を防止。
- .env 自動読み込みはデフォルトで有効だが、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト等の用途）。

### 既知の重要な設計上の注意点（注意 / Breaking changes 相当の箇所）

- OpenAI API キーは必須
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合に ValueError を送出します。実行前にキーを設定してください。

- DuckDB に関する互換性
  - DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックを行っています。将来の DuckDB バージョンではこの制約が変わる可能性がある点に注意してください。

- ルックアヘッドバイアス回避
  - 全ての AI / データ処理関数は date 引数（target_date）ベースで計算し、datetime.today()/date.today() を参照しないように設計されています。これによりバックテスト等でのルックアヘッドを防止しますが、呼び出し側は適切な target_date を渡す必要があります。

- 時刻・タイムゾーン取り扱い
  - news_nlp のニュースウィンドウは JST を基準に定義し、DB の比較では UTC naive datetime を使う実装です。外部連携や DB のタイムゾーン保存方針に合わせて利用してください。

- 自動 .env ロードの優先順位
  - OS 環境変数 > .env.local > .env の順で上書きされます。.env.local は .env を上書きするため、機密情報や開発/本番差分の運用に注意してください。

### テスト支援・運用上の配慮

- OpenAI 呼び出しはモジュール内で独立したラッパー関数（_call_openai_api）として実装しており、unittest.mock.patch によって差し替え可能です（単体テスト容易性を考慮）。
- LLM 呼び出しでのエラーは多くの場合フェイルセーフ（スコア = 0.0、または該当銘柄スキップ）として扱い、システムの全体停止を防止する方針です。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（現状は __all__ に名前のみ用意）
- テストカバレッジの拡充、CI/CD の整備
- J-Quants / kabu ステーション連携の拡張とデプロイ手順の文書化

問い合わせ・貢献方法
- バグ報告、機能要望、プルリクエストはリポジトリの Issue / PR を利用してください。
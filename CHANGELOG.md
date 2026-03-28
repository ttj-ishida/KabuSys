KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

Unreleased
----------

0.1.0 - 2026-03-28
------------------

Added
- 初回リリースとしてパッケージ kabusys を追加。
  - パッケージ公開バージョン: 0.1.0
  - パッケージトップ: src/kabusys/__init__.py により version と公開モジュール一覧を定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートを .git または pyproject.toml から特定して .env/.env.local を読み込む（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式やクォート・エスケープ、行末コメントなどの実用的な構文に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等のプロパティで設定値を安全に取得。
    - 必須値未設定時は ValueError を送出。
    - env / log_level の検証ロジックを実装（許容値チェック）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - タイムウィンドウ、1 銘柄あたりの最大記事数・文字数トリム、バッチ処理（_BATCH_SIZE）を実装。
    - レートリミット・ネットワーク切断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンス検証（JSON 抽出、results 配列、code の照合、スコアの数値検証）、±1.0 でクリップ。
    - 成功した銘柄のみを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）する挙動。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）、LLM 呼び出し（gpt-4o-mini）による JSON レスポンス処理、リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - スコア合成・閾値によるラベル決定・market_regime テーブルへの冪等書き込みを実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- データプラットフォーム / ETL (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを管理するユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未登録の場合は曜日ベース（平日のみ営業日）でフォールバック。
    - 夜間バッチ更新 calendar_update_job(conn, lookahead_days) を提供し、J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass により ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を構造化して返却。
    - 差分更新・バックフィル・品質チェック（quality モジュールと連携）・idempotent 保存（jquants_client の save_* を想定） の設計方針に基づく実装骨格。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得などを実装。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ（研究用）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比）、バリュー（PER、ROE）を DuckDB の prices_daily/raw_financials から計算。
    - データ不足時の None 取扱いやログ出力を実装。
    - 公開 API: calc_momentum, calc_volatility, calc_value。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応、入力検証。
    - IC（Information Coefficient：Spearman ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
  - data.stats の zscore_normalize を再エクスポートし、研究ワークフローで利用可能に。

Changed
- （初版のため Change 履歴はありません）

Fixed
- （初版のため Fix 履歴はありません）

Notes / 実装上の重要事項
- OpenAI の利用
  - デフォルトで gpt-4o-mini を使用し、JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待する設計。
  - テスト容易性のため _call_openai_api をモジュール内部で分離しており、ユニットテストで差し替え可能。
  - API エラー時はフェイルセーフとして処理を継続する設計（スコアに 0.0 を用いる、もしくは当該チャンクをスキップ）。
- ルックアヘッドバイアス防止
  - 各モジュール（score_news / score_regime / 各種計算）は内部で date.today() 等に依存せず、呼び出し側が target_date を与える設計。
  - DB クエリは target_date を境に排他条件を付けて未来データを参照しないよう配慮。
- DuckDB 互換性
  - executemany に空リストを渡さない等、DuckDB（既知のバージョン差分）を考慮した実装がある。
- 環境変数の保護
  - .env ロード時に既存の OS 環境変数を保護する仕組みがある（.env.local で上書き可能だが OS 変数は保護）。

Security
- 本リリースでは API キー等の機密情報は環境変数経由で扱う設計。環境変数の未設定時は ValueError を送出し、平文の設定ファイルの取り扱いについては .env.example を参照するよう案内する。

Acknowledgements
- 本 CHANGELOG は現行のコードベースの解析に基づいて作成しています。実行環境や外部依存（OpenAI SDK / DuckDB / J-Quants クライアント等）のバージョンによって挙動は変わる可能性があります。
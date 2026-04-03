# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本 CHANGELOG はリポジトリ内のソースコードから機能・設計・修正点を推測して作成した初期の変更履歴です。

## [Unreleased]

### Added
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョン `0.1.0` を設定。
  - パッケージ外部公開 API: data, strategy, execution, monitoring を __all__ として公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（読み込み順: OS 環境 > .env.local > .env）。
  - プロジェクトルートの自動検出ロジックを追加（.git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーで export 形式、クォート内のエスケープ、行末コメント等に対応。
  - 既存 OS 環境変数を保護する protected オプションを実装（.env.local の上書き動作制御）。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境種別等の取得を提供。
  - 必須環境変数未設定時は ValueError を送出する _require() を導入。
  - KABUSYS_ENV, LOG_LEVEL 等の許容値チェックを追加。

- データ基盤 (kabusys.data)
  - ETL パイプラインの公開型 ETLResult を追加（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - pipeline モジュールを実装し、差分更新・バックフィル・品質チェックの枠組みを定義。
  - ETLResult dataclass に実行結果の構造化（品質問題 / エラーメッセージ / 書込件数 等）を追加。
  - calendar_management モジュールを実装し、JPX カレンダー管理・営業日判定・夜間バッチ更新（calendar_update_job）を実装。
    - market_calendar が未取得時の曜日ベースフォールバック、DB 値優先の設計。
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
    - カレンダー更新時のバックフィルと健全性チェックを実装。
  - jquants_client 経由のデータ取得・保存に連携する設計（jquants_client 呼び出し箇所を想定）。

- リサーチ・ファクター群 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などモメンタム系指標を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials から最新財務データを取得し PER・ROE を算出。
    - 計算は DuckDB の prices_daily / raw_financials を直接参照する SQL ベース実装。
    - データ不足時は None を返す等、堅牢性を確保。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（例: 1,5,21）に対する将来リターンを一括取得。
    - calc_ic: Spearman（ランク相関）による IC 計算を実装（同順位は平均ランク扱い）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を提供。
    - 外部依存を可能な限り排し、標準ライブラリ + DuckDB のみで実装。

- AI（NLP）によるニュース解析 (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）の JSON モードで一括スコアリング。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事数・文字数上限（トリム）、レスポンス検証、スコアクリップ（±1.0）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライを実装し、非致命的失敗時はスキップして処理継続。
    - _validate_and_extract によるレスポンスの厳密バリデーション（JSON 抽出、results キー、型チェック、未知コード無視等）。
    - 書き込みは ai_scores テーブルの対象コードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（lookahead バイアス防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）、スコア合成・クリップ、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - OpenAI 呼び出しは別関数化してモジュール分離を保持。

- 共通設計上の注意点
  - 全ての「日付基準」処理は datetime.today() / date.today() を参照しない設計思想（ルックアヘッドバイアスの回避）。
  - DuckDB を主たるローカル分析 DB として利用。
  - DB 書き込みは可能な限り冪等に（DELETE → INSERT / ON CONFLICT など）。
  - API キーは引数注入または環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）で提供。未設定時は明示的に ValueError を投げる。

### Changed
- （初回リリースのため無）

### Fixed
- （初回リリースのため無）

### Security
- OpenAI 等の外部 API キーは Settings を通じて取得し、欠落時はエラーを発生させることで誤った運用を防止。

### Notes / Implementation details
- OpenAI は gpt-4o-mini と JSON Mode（response_format={"type": "json_object"}）を前提に実装。ただしレスポンスパースの回復処理を備え、前後ノイズが混入しても {} を抽出してパースを試みる。
- リトライ挙動や閾値 (_MAX_RETRIES, _RETRY_BASE_SECONDS, スコアクリップ等) はコード内定数で調整可能。
- calendar_update_job は J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）に依存しており、API エラー・保存エラー時は 0 を返すフェイルセーフ設計。
- news_nlp / regime_detector といった AI 関連処理はテスト環境で外部 API 呼び出しを差し替え可能な拡張ポイントを持つ。

---

開発・運用に関する問い合わせや、想定されるリリースノートの追記希望があればお知らせください。コードの追加変更があればそれに合わせて CHANGELOG を更新します。
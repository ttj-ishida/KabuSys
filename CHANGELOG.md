# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトは現在セマンティックバージョニングを使用しています。

## [Unreleased]

（現在の作業中の変更はありません）

## [0.1.0] - 2026-03-29

最初のリリース。日本株自動売買基盤のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - バージョン識別子を __version__ = "0.1.0" として設定。

- 設定管理
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探す）から自動読み込みする仕組みを実装。
  - OS 環境変数の保護（上書き禁止）と .env.local による上書き実装。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - _parse_env_line によるシェル互換の .env パース（コメント、export プレフィックス、クォート／エスケープ対応）。
  - Settings クラスを追加し、J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などをプロパティで取得可能に。
  - env, log_level のバリデーション、is_live/is_paper/is_dev のユーティリティを提供。

- データプラットフォーム（Data）
  - ETL パイプラインの公開インターフェース ETLResult（kabusys.data.pipeline / kabusys.data.etl）。
  - market_calendar を操作するマーケットカレンダー管理モジュール（kabusys.data.calendar_management）を追加。
    - 営業日判定、前後の営業日探索、期間内営業日リスト取得、SQ日判定のユーティリティを実装。
    - DB にデータがない場合は曜日（平日）ベースのフォールバックを行う設計。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存を実行可能。
  - ETL パイプラインの骨格（kabusys.data.pipeline）を追加。
    - 差分更新、バックフィル、品質チェックのための ETLResult データクラスを実装。
    - DuckDB を用いた最終日取得ユーティリティ等を提供。
  - jquants_client（参照）との連携点を考慮した設計（fetch/save 関数を呼び出す想定）。

- 研究（Research）
  - ファクター計算ライブラリ（kabusys.research）を追加。
  - calc_momentum / calc_volatility / calc_value を実装（kabusys.research.factor_research）。
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR、平均売買代金・出来高比率、PER/ROE 等を DuckDB の prices_daily / raw_financials を用いて計算。
    - 欠損・データ不足時に None を返す設計。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、ペアが 3 件未満で None を返す）。
    - ランク化ユーティリティ rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージから zscore_normalize を再エクスポートするための初期統合を用意。

- AI（自然言語処理 / レジーム判定）
  - ニュース NLP スコアリングモジュール（kabusys.ai.news_nlp）を追加。
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換する calc_news_window を実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、1銘柄あたりの最大記事数・文字数制限、レスポンスのバリデーション、スコア ±1.0 でクリップ。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライ実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）対応。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api をモック差替え可能に実装。
  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）を追加。
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime を算出・書き込み。
    - マクロニュース抽出はキーワードベース（多数の日本・米国マクロ語彙）でフィルタ。
    - OpenAI 呼び出しは独立実装（モジュール分離）。API のリトライ・失敗時のフォールバック（macro_sentiment=0.0）。
    - ルックアヘッドバイアス回避設計（target_date 未満のデータのみを使用、datetime.today() を参照しない）。
    - market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - AI モジュールから外部に公開する関数として score_news と score_regime を提供（音声などは含まない）。

### 変更 (Changed)
- （初版のため変更履歴はなし）

### 修正 (Fixed)
- （初版のため修正履歴はなし）

### セキュリティ (Security)
- .env の読み込みにおいて OS 環境変数を上書きしないデフォルト動作を採用。意図しない環境変数上書きを防止。

### 設計上の注記 / 既知の挙動
- ルックアヘッドバイアス防止のため、日付処理はすべて target_date ベースで行い、datetime.today() / date.today() を直接参照しない関数設計を採用している（score_* / calc_* 系）。
- OpenAI API 呼び出しは JSON Mode を利用し、レスポンスの整形・パースに頑健化対策（前後の余計なテキスト抽出等）を実装。
- DuckDB の executemany に空リスト渡しが許容されないバージョンを考慮して、INSERT/DELETE 実行前に空チェックを行う実装。
- エラー時はフェイルセーフとして処理を継続する設計（AI API の恒常的失敗時にスコアを 0.0 とする、部分失敗時に他コードの既存スコアを保持する等）。
- テスト容易性のため、OpenAI 呼び出し箇所（_call_openai_api）や内部関数を unittest.mock.patch で差し替え可能に設計している。

---

作業や導入に際しては README や DataPlatform.md / StrategyModel.md 等の設計文書を参照してください（実装はそれらのセクションに基づいて行われています）。
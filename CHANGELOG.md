# Changelog

すべての重要な変更を Keep a Changelog の形式で記録します。
このファイルでは、主要なリリースや機能追加・バグ修正・設計上の重要な決定を日本語でまとめています。

注意: 以下の履歴は提供されたコードベースの内容から推測して記載しています。

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-03-31
初回リリース。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージエントリポイント `src/kabusys/__init__.py` を追加。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン `0.1.0` を設定。

- 環境設定・ローダー
  - `kabusys.config.Settings` による環境変数ベースの設定取得を実装。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動読み込みを無効化可能。
  - .env パーサーは以下に対応:
    - `export KEY=val` 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ
    - インラインコメント処理（クォート無しの場合の `#` 扱い）
  - 設定項目（プロパティ）を定義: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。入力検証（env 値のリストチェック、ログレベル検証）を実施。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp.score_news`:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを取得。
    - バッチ処理（最大 20 銘柄／API コール）、1 銘柄あたりの記事数・文字数上限実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で実施し、部分失敗時には既存スコアを保護。
    - テスト容易性のため、内部の OpenAI 呼び出しをパッチ可能に実装（_call_openai_api の差し替え）。
  - `kabusys.ai.regime_detector.score_regime`:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・保存。
    - DuckDB の prices_daily / raw_news を参照、OpenAI を用いたマクロセンチメント評価、API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、例外時に ROLLBACK を試行して適切に伝播。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比率）、バリュー（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算で、営業日ベースの窓や不足時の None ハンドリングを実装。
  - `kabusys.research.feature_exploration`:
    - 将来リターン算出（calc_forward_returns）、IC（Spearman ランク相関）算出（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。
  - `kabusys.research.__init__` で主要関数群をエクスポート（zscore_normalize は data.stats から）。

- データプラットフォーム（Data）
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等を提供。
    - market_calendar の有無に応じた DB 優先ロジックと曜日ベースのフォールバック、最大探索日数制限、安全性チェック、夜間バッチ更新 job（calendar_update_job）を実装。
    - calendar_update_job は J-Quants クライアント経由で差分取得・保存、バックフィル日数と健全性チェックを実装。
  - `kabusys.data.pipeline`:
    - ETL パイプラインの主要ユーティリティと方針を実装（差分更新、保存、品質チェック）。
    - `ETLResult` データクラスを提供し、実行結果・品質問題・エラー概要を集約、辞書化メソッドを持つ。
  - `kabusys.data.etl` で ETLResult を再エクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- .env パーサでのエスケープ・クォート処理、インラインコメント扱い、`export` プレフィックス対応など、実運用での多様な .env フォーマットに耐える実装。
- DuckDB の executemany に関する互換性問題（空リスト禁止）を考慮したガード（空リストなら実行しない）を ai / pipeline の書き込み処理に組み込み。
- OpenAI 呼び出し周りでの各種例外（RateLimitError / APIConnectionError / APITimeoutError / APIError）を明確に分類し、5xx とそれ以外での挙動を分けることでより堅牢なリトライ戦略を実装。

### セキュリティ (Security)
- なし（公開コードから推測した限り）。

### 備考（設計上の重要点）
- 「ルックアヘッドバイアス防止」のため、いかなる箇所も datetime.today() / date.today() を直接的に参照せず、外部から与えた target_date を用いる設計を採用。再現性・テスト可能性を重視。
- DB 書き込みは冪等性を重視（DELETE → INSERT、トランザクション処理とロールバック対策）。
- OpenAI 連携は JSON モードを使用し、レスポンスバリデーションを厳密に行う。API 呼び出し箇所はユニットテストで差し替え可能に実装。
- DuckDB を主なデータ格納・集計エンジンとして使用し、SQL と Python の組合せで解析処理を実装。

---

- 参考: 本 CHANGELOG はソースコードのコメント、関数名、処理フローの記述から推測して作成しています。実際の変更履歴（コミット単位）はバージョン管理履歴をご確認ください。
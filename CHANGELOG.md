# Changelog

すべての変更は「Keep a Changelog」の形式に準拠しています。  
このファイルはコードベース（初期リリース）から推測して作成しています。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-27
初回リリース。本バージョンでは日本株自動売買システムのコア機能（データ取得/ETL、カレンダー管理、リサーチ用ファクター計算、AIベースのニュース/レジーム判定、設定管理など）を実装しています。

### Added
- パッケージ基礎
  - kabusys パッケージ（__version__ = 0.1.0）を追加。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に登録。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env の柔軟なパース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント判定等に対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定値を取得する API を実装（必須項目は未設定時に ValueError を発生）。
  - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）
    - 市場カレンダー取得・夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合の曜日ベースのフォールバック（週末除外）。
    - 安全性: 最大探索日数制限、バックフィル、健全性チェック等を実装。
  - ETL パイプライン（pipeline）
    - 差分取得・保存・品質チェックの設計方針に準拠した ETLResult データクラスを実装（to_dict による品質問題の整形等を含む）。
    - DuckDB 周りのユーティリティ（テーブル存在確認や最大日付取得）。
  - etl モジュール外部公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ処理／チャンク化（最大 20 銘柄／API コール）、1銘柄あたりの記事数および文字数トリム機能。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとスコアクリッピング（±1.0）。
    - ai_scores テーブルへの冪等的な書き込み（対象コードの DELETE → INSERT）。
    - calc_news_window: JST 指定のニュースウィンドウ計算（UTC 変換を前提）。
    - テスト容易性: _call_openai_api のモック差し替えを想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードによる raw_news 抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API リトライ・フェイルセーフ: API 失敗時は macro_sentiment = 0.0 を使用。
    - レジーム判定ロジックでは lookahead バイアスを避けるため target_date 未満のデータのみ使用。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、ma200 乖離、ATR（20 日）、20 日平均売買代金、出来高比率、PER/ROE（raw_financials 組合せ）などのファクター計算を実装。
    - DuckDB を使った SQL ベース実装で、データ不足時の None 取り扱い。
  - feature_exploration:
    - 将来リターン calc_forward_returns（柔軟な horizon 設定、入力検証）。
    - IC（Information Coefficient）計算（スピアマンランク相関）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties 対応）。
    - factor_summary（count/mean/std/min/max/median の計算）。
  - research パッケージ公開 API を整備（主要関数を __all__ で再エクスポート）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし。コード内で以下の堅牢化を実装）
  - OpenAI API 呼び出しでの各種エラー（RateLimit, 接続, タイムアウト, 5xx）に対する再試行処理とフォールバックを実装。
  - DuckDB executemany の空リスト制約を回避する保護コードを追加（空パラメータ時は呼び出さない）。
  - .env 読み込み失敗時に警告を出力して処理継続。

### Security
- OpenAI API キー必須（api_key 引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError を送出して明示的にエラー扱い。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト用途を想定して安全に制御可能）。

### Notes / Known limitations
- news_nlp の出力フォーマットは現状 strict JSON（results キー）を期待。LLM 応答が期待フォーマットを満たさない場合は該当チャンクはスキップされる（安全側の設計）。
- value ファクターでは PBR・配当利回りは未実装。
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_regime, market_calendar 等）に依存するため、正しいテーブルが存在することが前提。
- 日付処理は lookahead バイアス回避のため datetime.today() / date.today() を直接参照しない関数設計を採用（ただし calendar_update_job は実行日 today を使用する）。
- OpenAI クライアント呼び出しは gpt-4o-mini と JSON mode を利用する想定。将来的にモデル変更が必要な場合は該当定数を更新。

以上が初期リリース（0.1.0）の主な追加・設計要点です。テストや運用で発見された不具合・改善点は次リリースで反映してください。
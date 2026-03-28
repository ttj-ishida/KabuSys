# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しており、セマンティックバージョニングを使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として公開。
  - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定を自動読み込みする仕組みを導入（プロジェクトルートは .git または pyproject.toml から探索）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - POSIX ライクな .env 解析器を実装（export プレフィックス対応、クォートやバックスラッシュエスケープ、行内コメント処理など）。
  - .env 読み込み時の保護キー保護（OS 環境変数を上書きしない `protected` 機能）。
  - 環境変数取得用 Settings クラスを実装。J-Quants / kabu ステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。
  - 設定値のバリデーション（有効な env 値・ログレベルチェック）と利便性プロパティ（is_live, is_paper, is_dev）を追加。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（-1.0〜1.0）を評価する score_news() を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する calc_news_window()。
  - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフの実装。
  - レスポンスの堅牢なバリデーションとパース（JSON 前後の余計なテキストから {} を抽出する処理含む）、スコアのクリップ、部分失敗時に既存データを保護する書き込み戦略（DELETE → INSERT、部分書き込み可能）。
  - テスト容易性のため OpenAI コールを差し替え可能（_call_openai_api をパッチ可能）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull / neutral / bear）を算出する score_regime() を実装。
  - MA 計算、マクロ記事抽出、LLM 評価（gpt-4o-mini）、スコア合成、閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を含む。
  - API エラーやパース失敗時はフェイルセーフで macro_sentiment = 0.0 にフォールバックするロバスト設計。
  - LLM 呼び出しロジックは news_nlp と意図的に分離（モジュール結合の回避）、テスト差し替え可能。

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job() と市場カレンダーに基づく営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar 未取得時の曜日ベースフォールバック、DB 値優先の一貫した挙動、最大探索範囲制限で無限ループ防止。
    - J-Quants クライアント経由での取得処理と健全性チェック（未来日付の異常検出、バックフィル）を実装。
  - ETL パイプライン (pipeline)
    - ETL 実行結果を表す ETLResult データクラスを追加（取得数・保存数・品質問題・エラーの集約、has_errors / has_quality_errors プロパティ、辞書変換）。
    - 差分更新・バックフィル・品質チェック・Idempotent 保存の設計方針を実装するための基盤を整備。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等のボラティリティ/流動性ファクターを計算。
    - calc_value: raw_financials を使った PER / ROE の計算（target_date 以前の最新財務データを使用）。
    - DuckDB + SQL ベースの高効率実装。データ不足時は None を返す方針。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を一括で取得可能。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（Information Coefficient）を計算。
    - rank: 同順位は平均ランク扱いの堅牢なランク関数を実装（丸めによる ties 対策）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - 研究用ユーティリティの再エクスポート（zscore_normalize など外部モジュール連携）。

- その他
  - DuckDB をデータ層の主要ストレージとして想定し、各モジュールは DuckDB 接続を受け取る設計。
  - OpenAI クライアントの使用箇所で api_key を引数注入可能にしてテスト容易性を確保。
  - 多数の関数で「ルックアヘッドバイアス防止」のため datetime.today() / date.today() を直接参照しない実装方針を採用（target_date を明示的に渡す）。

### Changed
- （該当なし）初回リリースのため変更履歴はありません。

### Fixed
- （該当なし）初回リリースのためバグ修正履歴はありません。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 環境変数と .env の読み込みにおいて OS 環境変数の保護（protected set）を実装。APIキー等の誤上書きを抑止。

---

注意:
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートに必要な追加情報（実際のリリース日、変更の責任者、関連チケット等）があれば適宜追記してください。
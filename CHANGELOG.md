# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」に準拠します。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要コンポーネントと機能を実装しました。

### Added
- パッケージ基盤
  - パッケージルートの初期化（kabusys.__init__）とバージョン定義を追加（__version__ = "0.1.0"）。公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を探索）。
  - .env のパース機能を強化：コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
  - OS 環境変数を保護する protected 設定（.env.local の上書き時に OS 環境変数を踏みつぶさない）。
  - 必須環境変数の取得ヘルパー _require と、各種設定プロパティを追加（J-Quants、kabuステーション、Slack、DB パス、環境判定、ログレベル検証等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - API 呼び出しのバッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数制限、JSON Mode を用いた厳密なレスポンス処理を実装。
    - リトライ／エクスポネンシャルバックオフ（429、ネットワーク断、タイムアウト、5xx など）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト形式確認、コード照合、数値チェック）、スコアの ±1.0 クリップを実装。
    - テスト容易性のため OpenAI 呼び出し箇所をモック可能に設計（kabusys.ai.news_nlp._call_openai_api を差し替え可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装（score_regime）。
    - マクロ検出用キーワード群を定義し、raw_news からタイトルを抽出して LLM に渡す実装を追加。
    - OpenAI 呼び出し（gpt-4o-mini）で JSON レスポンスを期待し、リトライ・バックオフを実装。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - MA200 計算やデータ不足時のフォールバック（中立値）、ルックアヘッドバイアス防止（target_date 未満のデータのみ使用）を明確に実装。
    - テスト用に _call_openai_api をモック可能に設計。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
    - 営業日判定・次/前営業日の取得・期間内営業日リスト取得・SQ 日判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日の曜日ベースフォールバック設計。最大探索範囲を設定して無限ループを防止。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants から差分取得→冪等保存（save_market_calendar 呼び出し）を行う。バックフィル・健全性チェックを実装。

  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約できるように実装。
    - 差分更新、バックフィル、品質チェックの設計方針を定義（pipeline モジュールに準備）。kabusys.data.etl で ETLResult を再エクスポート。

  - DuckDB 互換性・安全性への配慮
    - executemany に空リストを渡さない防御（DuckDB 0.10 対策）。
    - 日付値の変換ユーティリティやテーブル存在チェック等のユーティリティを実装。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、20 日 ATR、流動性指標（20 日平均売買代金・出来高変化率）などを DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - raw_financials との結合による PER/ROE の算出を実装。
    - 設計上、本番口座・発注 API に接続しない安全な実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を持たない純粋 Python 実装。スピアマン ρ をランクに基づき計算。

- テスト支援 / 設計注記
  - 各モジュールでルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示的に渡す）。
  - OpenAI 呼び出しポイントを明確に分離してテスト容易性を確保（モック差し替え容易）。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Removed
- （初版のため削除履歴なし）

### Security
- OpenAI API キー未設定時は明示的に ValueError を送出して誤動作を防止するバリデーションを実装。
- 環境変数の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能。

## 既知の注意事項 / 設計上の制約
- OpenAI 呼び出しは gpt-4o-mini を前提としており、レスポンスは JSON Mode を期待する（実運用では API の挙動変化に注意）。
- DuckDB のバージョン差異（executemany の空配列扱い等）に配慮したコードが含まれます。古い/新しい DuckDB 実装での挙動確認を推奨します。
- ai モジュールは外部 API（OpenAI）と J-Quants のデータに依存するため、実行環境に適切な API キー・ネットワークアクセスが必要です。
- calendar_update_job や ETL 周りは J-Quants クライアント実装（jquants_client）に依存しています。API 実装や権限に応じた動作確認を行ってください。

---

貢献・バグ報告は issue を通じてお願いします。
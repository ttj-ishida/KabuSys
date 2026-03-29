# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期リリース向けの変更履歴です。

全般的な注意
- バージョンはパッケージメタデータ（src/kabusys/__init__.py の __version__）に合わせています。
- 記載内容はソースコードおよびドキュメンテーション文字列から推測した機能説明・設計意図に基づきます。

## [Unreleased]

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初期リリース: kabusys — 日本株自動売買・データプラットフォーム用ライブラリ。
  - バージョン: 0.1.0

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する機能を実装。
  - 自動読込はプロジェクトルート（.git または pyproject.toml を探索）を基準に行い、CWD に依存しない実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化をサポート。
  - .env のパーサーは以下の実装をサポート:
    - 空行・コメント行、先頭に `export ` を持つ行
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - 行内コメントの扱い（クォート外でスペース直前の `#` をコメントと認識）
  - 環境変数必須チェック関数 `_require` と Settings クラスを提供。主な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
  - OS 環境変数を保護する protected バインディング機構を導入（.env の上書きを制御）。

- AI 関連モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - 指定タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）に該当する raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode で一括評価。
    - バッチ処理: 最大 20 銘柄/チャンク。各銘柄は最新 10 記事／最大 3000 文字にトリム。
    - リトライ（指数バックオフ）: 429, ネットワーク断, タイムアウト, 5xx を対象に最大再試行。
    - レスポンスの堅牢なバリデーションと数値クリップ（±1.0）。
    - DuckDB への書き込みは部分冪等（該当 code の DELETE → INSERT）で実施し、部分失敗時に既存スコアを保護。
    - テスト容易性を考慮し、OpenAI 呼び出し箇所は差し替え可能（モジュール内で関数をモック可能）。
    - 出力 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使い、ルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウで抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを期待。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実施。
    - 出力 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- Research（ファクター／特徴量探索） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、20 日 ATR（atr_20）、流動性（20 日平均売買代金、出来高比率）などを DuckDB 内で計算する関数群を提供。
    - raw_financials を用いた Value 指標（PER, ROE）を提供。
    - データ不足時は None を返すなどの堅牢な取り扱い。
    - 出力形式は (date, code) を含む辞書のリスト。

  - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（デフォルトホライズン [1,5,21]）を提供。ホライズン検証（正の整数かつ ≤ 252）あり。
    - IC（Spearman の ρ）を計算する calc_ic（None 値や不足レコードに対する保護あり）。
    - ランク変換関数 rank は同順位の平均ランク処理と丸め（round(...,12)）で ties 対応。
    - factor_summary による基本統計量（count, mean, std, min, max, median）を提供。
  - research パッケージの __all__ に主要 API を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- Data（データ取得・管理） (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX マーケットカレンダー管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日（平日）でのフォールバックを実装。
    - calendar_update_job により J-Quants から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
    - バックフィル、健全性チェック（将来日付の異常検出）、最大探索日数制限などの保護ロジックを実装。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し、ETL の取得数・保存数・品質チェック結果やエラー概要を収集・出力可能。
    - 差分取得のためのユーティリティ（テーブル存在チェックや最大日付取得）を実装。
    - デフォルトのバックフィル、カレンダー先読みなど運用上の設定を定義。
    - data.etl モジュールで ETLResult を再エクスポート。

- パッケージ初期エクスポート
  - src/kabusys/__init__.py で主要サブパッケージ名を __all__ に公開（data, strategy, execution, monitoring）。

### 変更 (Changed)
- 初期リリースのため、既存コード整備・設計上の注記を含む多数の docstring と設計方針コメントを追加（モジュールごとに詳細な振る舞い・フェイルセーフの説明あり）。

### 修正 (Fixed)
- （初期リリースのため該当なし：既知の実装は設計上の保護と例外処理を多く含む）

### セキュリティ (Security)
- OpenAI API キー等の必須情報は Settings 経由で取得する設計で、環境変数が未設定の場合は ValueError を送出して明示的に止める実装。  
- .env の読み込みは OS 環境変数を上書きしない既定動作（上書きは .env.local と override=True により制御）で、意図しない機密情報の置換を防ぐ配慮あり。

### 既知の注意点 / 実装上の制約
- DuckDB バインドに関する互換性（executemany に空リストを渡せない等）を回避するためのガードが多数存在する（ai score 書き込み等）。
- 日時取り扱いはすべて date / naive datetime を使用し、ルックアヘッドバイアスを避ける設計になっている（datetime.today() や date.today() を参照しないことを意識）。
- OpenAI 呼び出しは JSON mode を期待しているが、稀に前後テキストが付与されるケースへ備えた復元ロジックや、API エラー時のフォールバック（macro_sentiment=0.0、スコア取得失敗はスキップ）を備えている。
- jquants_client（kabusys.data.jquants_client）との連携を前提としているが、実体は参照されており、外部 API 呼び出し失敗時には例外捕捉して ETL やカレンダー更新ジョブは安全に失敗する。

---

脚注:
- 本 CHANGELOG はソースコードのコメント・ドキュメンテーションから推測して作成しています。実際のリリースノートは運用上の決定（公開 API、互換性ポリシー、リリース日）に基づいて編集してください。
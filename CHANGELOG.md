CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

[0.1.0] - 2026-04-01
--------------------
Added
- パッケージ基礎
  - 初期バージョンをリリース。パッケージメタ情報は src/kabusys/__init__.py の __version__ = "0.1.0"。
  - パッケージ公開インターフェースとして data, strategy, execution, monitoring を __all__ で宣言。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロードの探索はパッケージファイル位置から .git または pyproject.toml を起点にプロジェクトルートを特定（CWD に依存しない）。
  - .env パース機能を強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの場合の行内コメント処理（'#' の前がスペース/タブの場合のみコメントとみなす）
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 既存の OS 環境変数は保護（protected set）して .env による上書きを制御。
  - Settings クラスを提供し、必須環境変数取得（_require）と各種プロパティ（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定など）を公開。KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装。
  - Path 型でのファイルパス展開（expanduser）や閾値の float 変換をサポート。

- AI モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメント (-1.0〜1.0) を取得して ai_scores テーブルへ保存。
    - タイムウィンドウ定義（JST ベース: 前日 15:00 ～ 当日 08:30）を calc_news_window として提供。
    - バッチ・チャンク処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数と文字数制限でトークン肥大化を防止。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - OpenAI レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード整合性、数値検証）とスコアクリッピング（±1.0）。
    - DuckDB 0.10 の executemany 空リスト制約に配慮した安全な DELETE → INSERT の置換ロジック（部分失敗時に既存スコアを保護）。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）に対応。未設定時は ValueError を送出。
    - フェイルセーフ: API 失敗時はそのチャンク／記事をスキップして処理継続。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定・保存。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を取得。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) の式で算出。閾値に基づき 'bull' / 'neutral' / 'bear' を決定。
    - OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）とレスポンスパースの堅牢化。
    - DB 書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）し、例外時は ROLLBACK を試行。

- 研究・ファクター分析 (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）および流動性指標を計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - DuckDB 上で SQL ウィンドウ関数を活用して効率的に計算。
    - データ不足時の None ハンドリングとログ出力。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: target_date の終値から指定ホライズン（デフォルト [1,5,21] 営業日）先までのリターンを一括クエリで取得。
    - IC（Spearman の ρ）計算（calc_ic）: code で結合してランク相関を算出。使用可能レコードが不足 (<3) の場合は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクを採用し、丸め誤差対策として round(..., 12) を適用。
    - ファクター列の統計サマリ（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージ公開 API を整備（__all__ に主要関数群を列挙）。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して market_calendar に冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録データがない場合は曜日ベース（平日）でフォールバック。DB 登録が一部しかない場合でも一貫した結果を返すよう実装。
    - 探索上限（_MAX_SEARCH_DAYS）やバックフィル日数（_BACKFILL_DAYS）等の安全策を導入。極端な last_date の将来日付は健全性チェックでスキップ。
    - jquants_client と連携する fetch/save 処理を想定し、例外時は安全にログを残して 0 を返す。

  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを実装（target_date, 取得数/保存数, quality_issues, errors を保持）。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新・バックフィル・品質チェック・idempotent 保存（jquants_client.save_* 想定）を行う ETL の設計方針とユーティリティを整備。
    - 内部ユーティリティでテーブル存在確認や最大日付取得を用意。
    - data.etl で ETLResult を公開。

- その他
  - ai パッケージの公開関数（score_news）が ai パッケージの __all__ に登録。
  - research/__init__.py で zscore_normalize を data.stats から再エクスポート。

Fixed
- 初期リリースにおける堅牢性改善:
  - OpenAI 呼び出しに対する細かい例外ハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError のステータス応答に基づく分岐）を追加。
  - JSON レスポンスパース失敗時に前後の不要テキストを切り出して復元する処理を追加（LLM の出力バラつきに耐性）。
  - DuckDB のバージョン差異（executemany の空リスト禁止）に配慮した実装で部分失敗時のデータ保護を実現。

Notes / Migration
- OpenAI API キーは各 AI 関数呼び出しに api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定して使用してください。未設定の場合は ValueError が発生します。
- DuckDB を用いる一部処理では executemany に空リストを渡すとエラーになるバージョン（例: 0.10）があるため、該当処理は事前に空チェックを行っています。
- .env 自動ロードはパッケージインポート時に行われます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制できます。

References
- パッケージ内部の設計方針や処理フローの詳細は各モジュールの docstring に記載されています。各ファイルを参照してください。
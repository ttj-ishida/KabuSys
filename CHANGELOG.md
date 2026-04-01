CHANGELOG
=========

すべての変更は Keep a Changelog 規約に従って記載しています。  
現在のバージョン: 0.1.0

[Unreleased]
------------

（なし）

0.1.0 - 2026-04-01
-----------------

初期リリース（初期機能セットの導入）

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"、公開モジュールの __all__ 設定）。
- 環境変数 / 設定管理
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local 読み込み実装：export 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理など堅牢なパーサ実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる設定プロパティ群の公開：
    - J-Quants / kabuステーション / Slack / DB パス（duckdb/sqlite）/監視閾値/環境モード（development/paper_trading/live）/ログレベルなど。
  - 必須環境変数未設定時の明確なエラーメッセージ（_require）。
- AI（自然言語処理）関連
  - news_nlp モジュール（score_news）：
    - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini + JSON Mode）へ最大 _BATCH_SIZE（デフォルト20）銘柄単位で問い合わせ。
    - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）を提供する calc_news_window。
    - レスポンス検証（JSON パースの耐性、results 配列の検証、未知コードの無視、スコアの ±1.0 クリップ）。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx サーバーエラー）を指数バックオフで実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - 書き込みは ai_scores テーブルへスコア取得済みコードのみ置換（部分失敗時に既存データを保護）。
  - regime_detector モジュール（score_regime）：
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、市場レジーム（bull / neutral / bear）を計算して market_regime に冪等書き込み。
    - マクロニュースは news_nlp の calc_news_window を利用して取得し、OpenAI へは独立した内部呼び出し実装を行いモジュール結合を抑制。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - API 呼び出しにもリトライ／5xx 判定ロジックを実装。
- データプラットフォーム関連
  - data.pipeline の ETLResult を公開（kabusys.data.etl から再エクスポート）。
  - ETLResult データクラス（取得件数、保存件数、品質問題リスト、エラーリスト、ユーティリティメソッド to_dict / has_errors / has_quality_errors）。
  - data.pipeline：差分取得／バックフィル／品質チェックを想定した設計（J-Quants クライアント経由の保存・品質検査フローを想定）。
  - calendar_management：
    - market_calendar 管理・夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得日のフォールバックは曜日ベース（土日非営業日）で一貫性を保つ実装。
    - カレンダー更新はバックフィル、健全性チェック（未来日付の異常検出）、J-Quants からの差分取得・保存を行う。
- リサーチ / ファクター
  - research.factor_research：
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を利用した SQL ベースの計算を採用し、prices_daily / raw_financials のみ参照する設計（実取引 API には触れない）。
    - データ不足時は None を返すなどの堅牢性を考慮。
  - research.feature_exploration：
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（例: 1,5,21営業日）で LEAD を用いて一括算出。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン相関（ランク）を実装、必要最小レコード数チェック。
    - ファクタ統計サマリー（factor_summary）とランク関数（rank）。
    - pandas 等外部依存を避け、標準ライブラリ中心で実装。
- 一貫した設計方針の明示
  - ルックアヘッドバイアス回避のため、内部処理は datetime.today()/date.today() を直接参照しない設計（target_date を引数で受け取る）。
  - DuckDB バインドの互換性（executemany の空配列回避等）を考慮した実装。
  - テスト容易性のため外部 API 呼び出しポイントに差し替えフックを用意。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Removed / Deprecated / Security
- N/A（初回リリース）

注意事項（既知の制約・運用メモ）
- 必須環境変数
  - OPENAI_API_KEY（score_news / score_regime を利用する際必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 利用想定）
  - KABU_API_PASSWORD（kabu API 利用想定）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
  - 上記は Settings プロパティで _require により未設定時に ValueError を送出する。
- データベース
  - デフォルト duckdb パスは data/kabusys.duckdb、sqlite は data/monitoring.db（Settings で上書き可）。
  - DuckDB のバージョン互換性に依存する箇所あり（executemany の空リスト扱い等）。
- OpenAI 呼び出し
  - gpt-4o-mini を前提に JSON Mode を利用（response_format による JSON object 期待）。
  - LLM レスポンスが不正な場合はフェイルセーフでスコア 0.0 または該当チャンクをスキップする実装。これにより API 部分不調時でも他処理を継続する。
  - テスト/モックのため _call_openai_api を patch 可能。
- calendar_management
  - market_calendar が未取得の場合は曜日フォールバック（祝日データがない限り土日を休日扱い）となるため、正確な祝日判定には JPX カレンダー取得を定期実行する必要あり。
- 未提供の外部モジュール
  - コードは jquants_client 等の外部クライアントモジュール（kabusys.data.jquants_client）が前提だが、ここでは実装内容の参照のみ（実体は別途用意）。
- ロギング・監視
  - 多くの関数で logger を用いた情報・警告出力を行う。運用時は適切なログ設定（LOG_LEVEL）と監視閾値設定（CPU/MEM/DISK）を推奨。
- テスト容易性
  - API 呼び出し箇所は差し替え可能なためユニットテスト作成が可能。ただし DuckDB 接続やサンプルデータを用意する必要あり。

将来検討事項（非網羅）
- ai モデルの差し替え/設定を外部化して柔軟に選択可能にする。
- ai 呼び出しのバッチ/コスト制御やローカルキャッシュの導入。
- ETL 周りの細かな品質チェックルールの実装とワークフロー化。
- Research モジュールのインターフェースを Pandas/Arrow 等と連携するオプション。

---

この CHANGELOG はコードベースのコメントと実装から推測して作成しています。実際のリリースノートとして公開する場合は、リリース時の差分・マージ記録に基づいて適宜調整してください。
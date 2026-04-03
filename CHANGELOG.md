Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本 CHANGELOG は提供されたソースコードから機能実装内容を推測して作成した初回リリース向けの変更履歴です。

Unreleased
- なし

[0.1.0] - 2026-04-03
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
    - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定・自動.env読み込み機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - export KEY=val 形式やクォート内のエスケープ、インラインコメントの扱いを考慮した .env パーサ実装。
  - 環境変数取得ユーティリティ Settings クラスを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等を参照。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）やリソース閾値（CPU/MEM/DISK）をプロパティとして提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live / is_paper / is_dev 帯域を提供。
  - 未設定必須環境変数に対しては明示的なエラーを発生させる _require 関数。

- データ取得・カレンダー管理（src/kabusys/data/*）
  - market_calendar を用いた営業日判定ロジック（calendar_management.py）
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DBにカレンダーがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 最大探索日数制限やデータの健全性チェックを導入。
  - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して保存・バックフィル対応）。
  - ETL パイプライン用の型 ETLResult と pipeline / etl のインターフェース（src/kabusys/data/pipeline.py, etl.py）
    - 差分更新、バックフィル、品質チェック連携の設計に基づく結果保持型を追加。
    - DuckDB を前提にしたテーブル存在チェック・最大日付取得などのユーティリティを実装。
  - jquants_client と quality モジュール（参照箇所あり）との連携を想定（差分取得→保存→品質チェックの流れ）。

- ニュースNLP / AI モジュール（src/kabusys/ai/*）
  - ニュースセンチメント付与機能 score_news（news_nlp.py）
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を計算する calc_news_window を実装。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄/チャンク）と JSON Mode 応答の検証・パース。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗時はログを出し該当チャンクをスキップ（フェイルセーフ）。
    - レスポンス検証ロジック（results リストの検査、コード一致チェック、数値検証、スコア ±1 にクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）を行い、部分失敗時に既存スコアを保護する設計。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 score_regime（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成（70% / 30%）して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロキーワードで raw_news をフィルタしてタイトルを取得、OpenAI で macro_sentiment を算出。
    - OpenAI 呼び出しは独立実装でリトライや API エラーのハンドリングを行い、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- リサーチ（因子・特徴量）モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M のリターン、ma200_dev（200日移動平均乖離）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などボラティリティ・流動性指標を計算。TR の NULL 伝播制御など品質に配慮した計算。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損時は None）・ROE を計算。
    - 設計方針として DuckDB 上の SQL と軽量 Python で処理を完結（本番指示系統へアクセスしない）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。ホライズン検証（1〜252）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を算出、3件未満は None を返却。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（Floating rounding により ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数（None 値を除外）。
  - research パッケージの __all__ で主要関数を再エクスポート。

- 汎用設計・品質に関する配慮
  - ルックアヘッドバイアス対策: news/regime/research の各処理は datetime.today()/date.today() を直接参照せず、必ず target_date 引数に基づいて処理。
  - DuckDB を前提とした SQL 実装と、executemany の空リスト問題（DuckDB 0.10）の回避ロジックを導入。
  - ロギングを随所に配置し、API エラーやパース失敗時の警告を明示。
  - OpenAI API キー取得は api_key 引数優先、なければ環境変数 OPENAI_API_KEY を使用。未設定時は明示的エラーを発生。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Notes / 注意事項
- OpenAI 呼び出しは gpt-4o-mini モデルと JSON Mode を想定しています。実行環境での API 利用量やレート制限に注意してください。
- .env 自動読み込みはプロジェクトルートの検出に基づくため、配布後に利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を注入することを推奨します（テスト時の制御が容易）。
- DuckDB のバージョン差異により一部 SQL バインディング動作が異なる可能性があるため、運用環境の DuckDB バージョンで十分なテストを行ってください。
- 本リリースはコードの内容から推測して作成した CHANGELOG です。実際の変更履歴やリリース日、貢献者情報はプロジェクトの正式履歴に合わせて更新してください。
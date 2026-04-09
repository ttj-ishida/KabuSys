# Changelog

すべての注目すべき変更履歴を記載します。本ファイルは「Keep a Changelog」仕様に準拠します。

- リリース日付のフォーマット: YYYY-MM-DD
- バージョン: セマンティックバージョニングを採用

## [0.1.0] - 2026-04-09

### 追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__="0.1.0"、公開モジュールを __all__ で定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーに以下の機能を実装:
    - コメント行、先頭の `export ` プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープ処理、インラインコメントの扱い（クォートあり/なしのケースの差異を考慮）。
  - 環境変数の必須チェック関数 _require と Settings クラスを提供。J-Quants / kabu / LINE / DB /監視 /システム設定などのプロパティを定義。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）、パス系設定は Path オブジェクトに正規化。
  - 環境 (KABUSYS_ENV) / ログレベル (LOG_LEVEL) の値検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) へバッチ送信してセンチメントスコアを生成。
    - 時間ウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST) を calc_news_window で実装。
    - バッチサイズ、記事数・文字数トリム、JSON Mode 出力検証、429/ネットワーク/タイムアウト/5xx 用の指数バックオフリトライを実装。
    - レスポンス検証関数 _validate_and_extract によりスキーマ検査（results 配列、code/score）と数値チェック、スコアの ±1.0 クリップを実施。部分失敗時に既存スコアを保護するため、書き込みは該当コードのみ DELETE → INSERT。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch で置換可能）。
    - エラー時はフェイルセーフにより例外を投げず処理を継続する設計。
    - パブリック API: score_news(conn, target_date, api_key=None) を提供。戻り値は書き込んだ銘柄数。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロセンチメント（LLM）を重み合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - レジーム合成: 70% * (ma200_dev scaled) + 30% * macro_sentiment、クリップ範囲は [-1, 1]。閾値によりラベル判定。
    - raw_news からマクロキーワードでフィルタしたタイトルを取得する処理を実装。
    - OpenAI 呼び出しは専用の _call_openai_api で行い、リトライ（429/接続/タイムアウト/5xx）とバックオフを実装。API 失敗時は macro_sentiment = 0.0 にフォールバック（例外は上位へ伝播しない）。
    - DB 書き込みは冪等化（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を行う。
    - パブリック API: score_regime(conn, target_date, api_key=None) を提供。OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。

- Research モジュール (src/kabusys/research)
  - factor_research.py:
    - モメンタム (1M/3M/6M リターン)、200日MA乖離、ATR（20日）、出来高/売買代金関連の流動性指標、PER/ROE（raw_financials を参照）を計算する関数を提供。
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB のウィンドウ関数を活用して一度のクエリで必要値を算出。
    - データ不足時の挙動（必要なレコード数に満たない場合は None）を明確化。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC 計算 calc_ic（スピアマンのランク相関を実装、最小レコード数チェック）。
    - rank（同順位の平均ランク処理）、factor_summary（count/mean/std/min/max/median の算出）を実装。
  - 研究用のユーティリティを束ねる __init__ を提供（zscore_normalize を data.stats から再エクスポート）。

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルに基づく営業日判定ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に登録がない場合は曜日ベースのフォールバック（休日: 土日）を採用し、一貫性のある振る舞いを保証。
    - カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由の差分取得、バックフィル、健全性チェック、冪等保存）。
    - DuckDB の日付値処理ユーティリティやテーブル存在チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
    - ETLResult データクラスを定義し、ETL の取得数 / 保存数 / 品質問題 / エラー集計を保持。
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）を想定した設計。ETLResult.to_dict() により品質問題を辞書化してログ出力可能。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- テストと運用に配慮した設計上の機能
  - OpenAI 呼び出しやスリープなどを差し替え可能にしてユニットテストが容易。
  - DuckDB における executemany の空リストバインド制約への対応（空時は実行しないガード）。
  - すべての時間帯ロジックで datetime.today()/date.today() に頼らない設計（ルックアヘッドバイアス防止を重視）。
  - IDempotent（冪等）な DB 書き込みを多用。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 (OPENAI_API_KEY) で解決。キー未設定時は ValueError を発生させ早期検出。
- .env 読み込み時に OS 環境変数を protected として上書き防止する仕組みを採用。

---

Note:
- 本 CHANGELOG はソースコードの実装内容（関数名、挙動、設計方針、保護策など）から推測して作成しています。実際のリリースノートやユーザー向けドキュメントでは、動作確認済みの変更点や既知の制約（サポートする OpenAI モデル、外部 API のバージョン依存等）を追記することを推奨します。
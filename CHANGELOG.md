Keep a Changelog
===============

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報
    - バージョン: 0.1.0
    - エントリーポイント: src/kabusys/__init__.py
    - __all__ に ["data", "strategy", "execution", "monitoring"] を公開

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたはOS環境変数から設定を自動ロード
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を基準に .git または pyproject.toml を探索して特定（CWD非依存）
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env パーサ: export KEY=val 形式、クォートとバックスラッシュエスケープ、インラインコメント取り扱いに対応
    - .env 読み込み時に OS 環境変数を protected として上書きを制御可能
  - Settings クラスによる型付プロパティ群
    - 必須環境変数取得で未設定時は ValueError を発生させる (_require)
    - キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境種別 (KABUSYS_ENV): development / paper_trading / live の検証
    - ログレベル (LOG_LEVEL) の検証

- AI モジュール (src/kabusys/ai)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄毎に記事を集約し OpenAI (gpt-4o-mini) に送信してセンチメントを算出
    - ニュースウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC に変換して比較）
    - バッチ処理: 最大 20 銘柄／リクエスト、1銘柄あたり最大10記事・3000文字にトリム
    - OpenAI JSON Mode を利用し、厳密な JSON を期待（レスポンスパースの回復処理を実装）
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ
    - レスポンス検証: results 配列・code/score 構造・数値チェック。スコアは ±1.0 にクリップ
    - 書き込み: ai_scores テーブルへ「DELETE（個別）→ INSERT」で冪等書き込み（部分失敗時の保護）
    - テストフレンドリー: API 呼び出し関数を patch で差し替え可能
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム判定
    - MA 計算は target_date 未満のデータのみを使いルックアヘッドを排除
    - マクロ記事はニュースからマクロキーワードで抽出し、最大 20 件まで LLM に投げる
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数を共有しない設計）
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - 出力: market_regime テーブルへ BEGIN/DELETE/INSERT/COMMIT による冪等書き込み
    - 主要しきい値・定数がコード内に定義（BULL/BEAR 閾値, retry ポリシー等）

- 研究（Research）モジュール (src/kabusys/research)
  - factor_research (calc_momentum, calc_value, calc_volatility)
    - モメンタム: 1M/3M/6M リターン、200日MA乖離（データ不足時は None を返す）
    - バリュー: raw_financials から直近財務データを取得して PER/ROE を算出
    - ボラティリティ／流動性: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - DuckDB SQL＋ウィンドウ関数で実装、外部 API を呼ばない（オフラインで安全に実行可能）
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
    - 将来リターン calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）に対応、ホライズン検証あり
    - IC（Information Coefficient）calc_ic: スピアマンのランク相関を実装（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median の統計サマリー
    - rank: 同順位処理（平均ランク）＋丸め処理で ties の誤差を抑制
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）

- データ（Data）モジュール (src/kabusys/data)
  - calendar_management (市場カレンダー管理)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未設定のときは曜日ベースのフォールバック（土日を非営業日扱い）
    - DB 登録値が優先、未登録日は曜日フォールバックで一貫性を保持
    - calendar_update_job: J-Quants から差分取得して市場カレンダーを冪等保存（バックフィルと健全性チェックを実装）
  - pipeline / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL の取得数／保存数／品質問題／エラーを集約）
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計
    - DuckDB のテーブル存在チェック、最大日付取得などのヘルパーを提供
    - jquants_client 経由の idempotent 保存（ON CONFLICT DO UPDATE）を想定

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の重要点（ドキュメント）
- ルックアヘッド対策: 多くの処理（AI スコアリング・レジーム判定・ETL ウィンドウ計算等）は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計
- フェイルセーフ: OpenAI 呼び出し失敗時は例外をバブルアップさせず、0.0（中立）やスキップで継続する箇所がある（ログ出力あり）
- トランザクションとロールバック: DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の形で行い、失敗時は ROLLBACK を実行。ROLLBACK に失敗しても警告ログを出す
- DuckDB 互換性: executemany に空リストを渡せない問題（DuckDB 0.10）に対応するガードを実装
- タイムゾーン: ニュースウィンドウ等は JST 表記を UTC に変換して DuckDB の UTC 保存データと比較（内部では naive UTC datetime を使用）
- OpenAI 関連
  - 使用モデル: gpt-4o-mini
  - JSON Mode を使う想定（厳密な JSON 出力を期待）。レスポンスが乱れるケースに備えた復元処理あり
  - OPENAI_API_KEY は関数引数または環境変数で解決。未設定時は ValueError を発生させる
- 環境変数と重要キー
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使う処理は OPENAI_API_KEY を必要とする（api_key 引数で注入可能）
- 設計方針の強調
  - 本システムの研究・指標算出部分は本番取引 API にアクセスしない（安全性）
  - 外部ライブラリ依存を極力抑え、テストしやすい（関数を差し替え可能）実装

Known limitations / To be aware
- OpenAI API 呼び出しは外部サービスに依存するため、API 変更により例外型や status_code の取り扱いが変わる可能性がある（コードは将来の SDK 変更に対して一部防御的に実装）
- 一部機能（例: PBR・配当利回り）は現バージョンでは未実装（calc_value の注記参照）
- news_nlp/regime_detector のプロンプトや重み・閾値はハードコードされており、チューニング用に将来的な設定化が望ましい

Authors / Contributing
- 初回実装として主要機能をまとめて提供。将来の拡張（設定外出し、プロンプト管理、より詳細な品質チェック等）を想定

（補足）本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は変更差分・コミット履歴・マイルストーンを参照して正式化してください。
# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

なお、本 CHANGELOG は提示されたコードベースから推測して作成した初期リリース向けの要約です。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ全体: 初期リリース。パッケージ名は kabusys、バージョン 0.1.0 を設定。
  - ファイル: src/kabusys/__init__.py

- 設定管理 (config):
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - .env のパースで以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォートのエスケープ処理
    - インラインコメントの扱い（クォートあり/なしでの違いを考慮）
  - auto-load の無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト用）。
  - OS 環境変数の保護（protected set）と .env 上書き制御（override）。
  - Settings クラスを提供し、アプリケーションで利用する主要設定をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。env / log_level のバリデーションを実装。
  - ファイル: src/kabusys/config.py

- AI: ニュースNLP スコアリング (news_nlp):
  - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで一括評価して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
  - 特徴:
    - スコアリングウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ。
    - 1チャンク最大 20 銘柄でのバッチ送信、1銘柄あたりの記事数・文字数制限（トリム）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、既知コードのみ採択、数値検証、±1.0 のクリップ）。
    - DuckDB の互換性を考慮した書き込み（部分成功時に既存スコアを保護するため、対象コードを限定して DELETE → INSERT を実行。executemany の空リスト回避などのワークアラウンド）。
    - テスト容易性のため _call_openai_api を patch 可能。
  - パブリック API: score_news(conn, target_date, api_key=None)
  - ファイル: src/kabusys/ai/news_nlp.py

- AI: 市場レジーム判定 (regime_detector)
  - ETF コード 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM, 重み 30%）を合成して、日次で市場レジーム（bull / neutral / bear）を判定。
  - 処理の特徴:
    - prices_daily と raw_news を参照して必要データを取得（ルックアヘッドバイアス回避のため target_date 未満のデータのみ使用）。
    - マクロ記事が存在する場合にのみ LLM を呼び出し、API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しは JSON モードを用い、リトライや 5xx 判定の処理を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時の ROLLBACK 処理）。
    - テスト用に _call_openai_api を差し替え可能。
  - パブリック API: score_regime(conn, target_date, api_key=None)
  - ファイル: src/kabusys/ai/regime_detector.py

- Research（リサーチ）モジュール:
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率。
    - calc_value: PER（EPS=0/欠損時は None）, ROE（raw_financials からの取得）。
  - 特徴量探索:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関 (IC) を計算（有効レコード 3 未満は None）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - zscore_normalize を data.stats から再エクスポート。
  - ファイル: src/kabusys/research/*

- Data（データプラットフォーム）:
  - calendar_management:
    - JPX カレンダー管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバックを使用。
    - calendar_update_job により J-Quants API から差分取得し、バックフィルと健全性チェック（未来日付の異常検知）を実装。jquants_client を利用した fetch/save のラッパーとエラーハンドリング。
    - ファイル: src/kabusys/data/calendar_management.py
  - ETL パイプライン:
    - ETLResult データクラスを公開し、取得・保存・品質チェック結果・エラー集約を保持。
    - DB テーブル存在チェックや最大日付取得などのユーティリティを実装。
    - Data pipeline の設計方針（差分更新、backfill、品質チェックの収集継続、id_token 注入可能）を反映。
    - ETLResult は kabusys.data.etl を通じて再エクスポート。
    - ファイル: src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
  - jquants_client と quality モジュールへの依存箇所を用意（実際の API クライアント実装は別モジュール想定）。

### 変更 (Changed)
- （新規リリースのため該当なし）

### 修正 (Fixed)
- （新規リリースのため該当なし）

### セキュリティ (Security)
- 環境変数読み込み時に OS 環境を保護する仕組みを導入（.env による意図しない上書きを防止）。

### 注意事項 / マイグレーションノート (Notes)
- OpenAI API キー:
  - score_news / score_regime は api_key 引数を受け取るが、指定がなければ環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出するので、呼び出し前にキーの設定が必要。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env / .env.local が自動的に読み込まれる。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- ルックアヘッドバイアス対策:
  - 各 AI / リサーチ関数は内部で datetime.today() / date.today() を参照せず、必ず caller が与える target_date に基づいて計算する設計になっている。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーとなるケースへのワークアラウンド（空チェック）や list 型バインドの不安定性回避を実装。
- フェイルセーフ:
  - OpenAI 呼び出しが失敗した場合、処理を中断せずにフォールバック値（macro_sentiment=0.0 等）やスキップで継続する実装が多く含まれる。
- テスト向けフック:
  - OpenAI 呼び出し箇所（_call_openai_api）を unittest.mock.patch 等で差し替え可能にしている。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は、変更差分やコミットログに基づく追記・修正を推奨します。）
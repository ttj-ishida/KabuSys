# Changelog

すべての注記は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・データ基盤・リサーチ・AI補助機能の骨格を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージのエクスポートポリシー: __all__ に data, strategy, execution, monitoring を定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定読み込みを行う自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動読み込みを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは以下に対応:
    - コメント行・空行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値でのインラインコメント処理（直前がスペース/タブの場合のみ）。
  - 上書き挙動:
    - override=False: 未設定キーのみセット
    - override=True: OS環境変数で保護されたキー（protected）を上書きしない
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack / データベースパス等（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
    - 環境: KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - ログレベル: LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のヘルパー。

- AI モジュール (src/kabusys/ai)
  - ニュースNLPスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）の JSON mode で一括評価して ai_scores に書き込む処理を実装。
    - 処理の特徴:
      - JST 基準の時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
      - 1チャンクあたり最大 20銘柄（_BATCH_SIZE）でバッチ呼び出し。
      - 1銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 429・ネットワーク断・タイムアウト・5xx はエクスポネンシャルバックオフでリトライ。
      - レスポンス検証とスコアの ±1.0 クリップ。
      - テスト用に _call_openai_api を patch して差し替え可能。
      - APIキーは引数または環境変数 OPENAI_API_KEY を使用。未指定時は ValueError。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次判定結果を書き込む機能を提供。
    - 特徴:
      - DuckDB からの ma200_ratio 計算（target_date より前のデータのみ使用しルックアヘッドを排除）。
      - マクロニュースは news_nlp.calc_news_window と raw_news を利用してフィルタ取得（マクロ向けキーワード群で抽出）。
      - OpenAI 呼び出し（gpt-4o-mini）で JSON を取得、リトライ/バックオフ、失敗時は macro_sentiment = 0.0（フェイルセーフ）。
      - スコア合成後に冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
      - テスト用に _call_openai_api を patch 可能。
      - APIキーは引数または環境変数 OPENAI_API_KEY。

- Data（データ基盤）モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar 管理、JPX カレンダーの夜間バッチ更新フローを実装（calendar_update_job）。
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - 設計上の配慮:
      - market_calendar が未取得時は曜日ベース（平日を営業日）でフォールバック。
      - DB に登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫した挙動。
      - 最大探索範囲 (_MAX_SEARCH_DAYS) による安全制限。
      - バックフィル（_BACKFILL_DAYS）や先読み（日数指定）をサポート。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETL の公開インターフェースとして ETLResult を実装・再エクスポート。
    - ETLResult dataclass により ETL の取得数・保存数・品質チェック結果・エラー概要を構造化して管理。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - DuckDB テーブル存在チェックや最大日付取得のヘルパーを提供。

- Research（リサーチ）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）/ 相対ATR（atr_pct）/ 20日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または欠損なら None）。
    - いずれも DuckDB の SQL ウィンドウ関数を用いた実装で、外部 API 呼び出しなし。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）で将来リターンを計算（営業日＝連続レコード数ベース）。
    - calc_ic: スピアマン（ランク）IC を計算（ペア数が 3 未満なら None）。
    - rank: 同順位は平均ランクを採るランク関数（丸めを入れて ties の扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- テスト・運用上の配慮
  - OpenAI 呼び出しラッパー関数（各モジュールの _call_openai_api）を patch してテストしやすくしている。
  - ルックアヘッドバイアスを避けるため、日付判定やウィンドウ計算で datetime.today() を参照しない設計（target_date ベース）。

### 変更 (Changed)
- 初回リリースにつき過去バージョンからの変更点なし（初期実装）。

### 修正 (Fixed)
- 初回リリースにつき修正点なし。

### セキュリティ (Security)
- OpenAI API キー等の機密情報は環境変数から取得する設計。デフォルトで .env 自動ロードが有効だが、テスト時等に `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

### 既知の注意点 / マイグレーションノート
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID のいずれかを Settings プロパティ経由で参照する際に未設定だと ValueError を送出します。運用前に .env を準備してください（.env.example を参照）。
- OpenAI 使用時:
  - 関数 score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。未設定時は ValueError。
  - API 利用時は gpt-4o-mini と JSON mode を前提とした応答整形・パース処理を行います。レスポンスに不要な前後テキストが混入するケースに備えて復元ロジックを組み込んでいますが、フォーマットが大きく変わるとパース失敗の可能性があります。
- DuckDB 互換性:
  - 一部処理は DuckDB の executemany の挙動に依存（空リスト不可であることを想定して防御コードあり）。DuckDB バージョン差異に注意してください。
- タイムゾーン:
  - データベース内の日時は UTC 想定（news ウィンドウ計算は UTC naive datetime を返す）。タイムゾーン混入を避けるため日付は date 型、日時は UTC ナイーブで扱う設計。

---

開発・運用にあたって追加情報や出力形式の調整が必要であればお知らせください。必要に応じて英語版やリリースノート（短縮版 / 詳細版）への変換も対応します。
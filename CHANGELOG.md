Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
（コードから推測して作成したため、日付や文言は実装内容に基づく推定です）

[Unreleased]

[0.1.0] - 2026-04-02 (推定)
-------------------------

Added
- 基本パッケージ構成
  - パッケージメタ情報として kabusys.__version__ = "0.1.0" を追加。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート判定は .git または pyproject.toml を起点に探索（CWD 非依存）。
    - .env/.env.local の読み込み順序: OS 環境変数 > .env.local > .env。.env.local は上書き（override）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサの高精度実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - 非クォート値の inline コメント (#) 判定は直前が空白/タブの場合のみコメントとみなす。
  - Settings クラスを提供し、各種必須/任意設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のデフォルト値を定義。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode による銘柄別センチメント評価を実装。
  - 主な特徴:
    - スコア計算対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄ずつ API 呼び出し。
    - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ（デフォルト上限3回）。
    - レスポンス検証: JSON パース、"results" リスト構造、code の照合、スコア数値性、有界チェック（±1.0 でクリップ）。
    - DB 書き込みは部分失敗に配慮し、成功した銘柄コードのみ DELETE → INSERT（トランザクション）で置換。
    - フェイルセーフ: API やパース失敗時はそのチャンクをスキップして継続。テスト容易化のため _call_openai_api を差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を実施。
  - 主な特徴:
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドを排除。
    - マクロニュースは news_nlp.calc_news_window で定義されたウィンドウからマクロキーワードでフィルタ。
    - OpenAI 呼び出し（gpt-4o-mini）の結果を JSON としてパースしスコア化。API 失敗時は macro_sentiment=0.0（中立）にフォールバック。
    - レジームスコア合成後に market_regime テーブルへ冪等的（DELETE / INSERT）に書き込み。トランザクション管理（BEGIN/COMMIT/ROLLBACK）を実装。
    - 再試行ロジックや 5xx の扱い、パース失敗時のログ出力など堅牢なエラーハンドリング。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義し ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約して返却。
    - 差分取得、バックフィル、保存（jquants_client の idempotent save_* を利用）、品質チェックの設計方針を実装。
    - DuckDB のテーブル存在チェック・最大日付取得等のユーティリティを提供。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない場合のフォールバックは曜日ベース（土日除外）。
    - next_trading_day / prev_trading_day は最大探索日数 _MAX_SEARCH_DAYS（60）で無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得 → save_market_calendar で冪等保存。バックフィル・健全性チェックあり（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - jquants_client との連携を想定（fetch/save の呼び出しを行う実装を参照）。

- リサーチ／ファクター（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高変化率）を DuckDB ベースの SQL で実装。
    - データ不足時の扱い（行不足で None を返す等）やスキャン期間のバッファ設計を反映。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、有効レコード 3 件未満で None を返す）。
    - rank と factor_summary（count/mean/std/min/max/median）を純粋 Python（外部依存なし）で提供。
    - ties の取り扱い（同順位は平均ランク）や浮動小数誤差対策（round）を考慮。

Changed
- （初回リリースのため該当なし。今後のバージョンで API 名や設定キーの変更等を記録予定）

Fixed
- （初回リリースのため該当なし。今後のバグ修正はここに追記）

Security
- OpenAI API キーは Settings 経由または関数引数で注入する方式を採用し、明示的な未設定チェックで ValueError を発生させることで誤設定を早期検出。

Notes / 実装上の重要ポイント（コードから推測）
- ルックアヘッドバイアス防止: 全ての分析・スコアリング関数は datetime.today()/date.today() を直接参照しない（target_date を引数で受け取る設計）。
- トランザクションとロールバック: DB 書き込みは BEGIN/COMMIT/ROLLBACK を用いて安全に行う実装。
- フェイルセーフ設計: 外部 API（OpenAI, J-Quants）失敗時でもシステム全体が停止しないよう、スコアを中立化したりチャンク単位でスキップする実装方針。
- テスト容易性: OpenAI 呼び出し等は内部関数を patch して差し替え可能にしてありユニットテストしやすい作り。

今後の予定（推奨）
- 戦略（strategy）、実行（execution）、監視（monitoring）モジュールの実装拡充・ドキュメント化。
- CI 上での .env 自動ロードの取り扱い明確化（KABUSYS_DISABLE_AUTO_ENV_LOAD の利用推奨）。
- 詳細な公開 API ドキュメント（各関数の入力/出力例、エラーケース）を追加。

----- 

参考:
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 主要依存想定: duckdb, openai

もし特定の変更点を強調したい、日付を確定したい、あるいはリリースノートを英語で整形したい場合はお知らせください。
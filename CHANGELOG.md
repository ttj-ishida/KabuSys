# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初回リリース。本パッケージは日本株向けのデータ基盤・リサーチ・AI スコアリング・市場レジーム判定を含むライブラリ群を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data / strategy / execution / monitoring をエクスポート（将来的なモジュール配置を想定）。
  - バージョン: `__version__ = "0.1.0"`。

- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出は .git / pyproject.toml に基づく）。
  - .env の行パーサを実装。以下の形式に対応:
    - 空行・コメント行（#）の無視
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなし値のインラインコメント処理（# の前が空白/タブのときコメント扱い）
  - .env と .env.local の読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は上書き（override）される。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用等）。
  - Settings クラスを追加。アプリケーションで利用する設定値をプロパティ経由で取得可能:
    - J-Quants, kabuステーション, Slack, データベースパス（duckdb/sqlite）等の設定プロパティを提供。
    - env 値（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性検証を実装。
    - 必須環境変数未設定時は明示的に ValueError を発生させる（_require）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に銘柄ごとのニュースセンチメントを計算する `score_news(conn, target_date, api_key=None)` を実装。
  - 時間ウィンドウの計算（JST 基準で前日 15:00 ～ 当日 08:30）を `calc_news_window` で提供。
  - OpenAI（gpt-4o-mini）を JSON mode で呼び出し、銘柄群を最大バッチサイズ（20）でまとめてスコアリング。
  - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
  - レスポンスの堅牢なバリデーションとスコア ±1.0 のクリップを行い、結果を `ai_scores` テーブルへ冪等的に書き込む（DELETE → INSERT）。
  - フェイルセーフ設計：API 失敗やパース失敗は例外を投げずスキップして処理継続。テスト用に _call_openai_api を差し替え可能。

- AI / 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を算出する `score_regime(conn, target_date, api_key=None)` を実装。
  - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワードでフィルタした記事取得、OpenAI 呼び出し、スコア合成、`market_regime` テーブルへの冪等書き込みを実装。
  - マクロキーワードの組（日本・米国・グローバル）を定義し、結果が不足する場合のフォールバック（macro_sentiment=0.0）を採用。
  - API 呼び出しでのリトライ/エラー処理、JSON パースエラー時のフォールバックを実装。
  - ルックアヘッドバイアス防止のため、データ取得は target_date 未満または指定ウィンドウのみを使用。datetime.today() を直接参照しない設計。

- リサーチ（定量ファクター） (kabusys.research)
  - factor_research モジュールを追加。DuckDB の prices_daily/raw_financials を用いて以下を算出:
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）
    - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio（20日ATR・流動性系）
    - calc_value(conn, target_date): per / roe（raw_financials の最新レコードを参照）
  - feature_exploration モジュールを追加:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）計算
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）計算
    - rank(values): 同順位は平均ランクとするランク関数
    - factor_summary(records, columns): count/mean/std/min/max/median の計算（Noneは除外）
  - 実装方針として外部依存（pandas 等）を使わず、DuckDB SQL と標準ライブラリで完結する設計。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management を追加。market_calendar を利用した営業日判定ロジックと夜間更新ジョブを提供:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - calendar_update_job(conn, lookahead_days=90): J-Quants からカレンダー差分取得 → market_calendar へ冪等保存。バックフィル・健全性チェックを実装。
    - カレンダー未取得時は曜日ベース（平日のみ営業）でフォールバック。
  - pipeline / etl（ETL 関連）を追加:
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を定義し etl モジュールで再エクスポート。
    - ETL 実行結果の要約・品質チェック用フィールドを提供（quality_issues, errors, has_errors, has_quality_errors, to_dict）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等を提供。
  - jquants_client（参照）との連携を想定した設計（fetch/save 関数を呼び出す箇所を実装）。

- 一貫した設計方針
  - ルックアヘッドバイアス防止: モジュール多くで datetime.today() / date.today() への依存を避け、外部から target_date を受け取る設計。
  - DuckDB をデータストア（ローカル分析用軽量DB）として利用する前提で SQL と Python を組み合わせた実装。
  - OpenAI API を使用する機能はテスト容易性のため差し替え可能な形に実装（内部呼出し関数をモック可能）。
  - API エラー時にはフェイルセーフ（スキップ or デフォルト値）で継続するポリシーを採用。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

備考:
- OpenAI を用いる機能を利用する際は環境変数 `OPENAI_API_KEY` を設定するか、各関数の api_key 引数にキーを渡してください。news_nlp/regime_detector は API キー未設定時に ValueError を投げます。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings 経由で参照されます。未設定時には明示的なエラーとなります。
- DuckDB テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提となります。テーブルの存在チェックや部分的フォールバックを組み込んでいますが、運用前にスキーマ準備を行ってください。
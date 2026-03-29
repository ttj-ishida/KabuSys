# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加 (kabusys.__init__)。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定/環境変数管理
  - 環境変数・設定読み込みモジュールを追加 (kabusys.config)。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export 形式、クォート文字列、インラインコメントなどの .env パースに対応。
    - OS環境変数を保護する override/protected ロジック。
    - 必須環境変数未設定時に ValueError を投げる _require ヘルパー。
    - Settings クラスを提供し、アプリケーションで使う主要設定値をプロパティ経由で取得可能:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL 検証
      - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理）関連
  - ニュース NLP スコアリングモジュール (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
    - バッチサイズ、トークン肥大対策（記事数・文字数制限）を実装。
    - JSON Mode を利用しレスポンスを検証・パースして ai_scores テーブルへ置換（DELETE → INSERT）で冪等保存。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフと最大リトライ処理。
    - API 失敗時は該当チャンクをスキップして他銘柄へ影響を与えないフェイルセーフ実装。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計。ターゲット日ベースでウィンドウを計算。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - 公開ユーティリティ: calc_news_window(target_date)

  - 市場レジーム判定モジュール (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースLLMセンチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出は内部キーワードリストに基づくフィルタ。
    - OpenAI 呼び出しは独立実装でテスト時に差し替え可能。
    - API リトライ/フェイルセーフ: API失敗やパース失敗時は macro_sentiment = 0.0 で継続し例外は起こさない（ただし DB 書き込み時の例外は上位へ伝播）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- データ（Data Platform）関連
  - カレンダー管理モジュール (kabusys.data.calendar_management)
    - JPX マーケットカレンダーを管理するロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job による J-Quants からの差分取得と market_calendar への冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）
    - DB にカレンダーがない場合は曜日ベース（土日非取引）でフォールバックする一貫した判定ロジックを提供。
    - 最大探索日数やバックフィル、健全性チェックを導入して無限ループや不整合を防止。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装し、ETL 実行結果の構造を定義（取得数・保存数・品質チェック結果・エラーメッセージ等）。
    - 差分更新、バックフィル、品質チェックを想定した設計。jquants_client と quality モジュールを利用する設計に基づく。
    - kabusys.data.etl で ETLResult を公開再エクスポート。

- 研究（Research）関連
  - ファクター計算モジュール (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、target_date に対する結果を (date, code) 形式の辞書リストで返却。
    - 不足データ時の None 扱い、ログ出力を実装。

  - 特徴量探索モジュール (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns)：任意ホライズンの将来リターンを LEAD を用いて算出。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman（ランク相関）を手作りで実装、3 件未満で None を返す。
    - ランク変換 (rank)：同順位は平均ランク、浮動小数の丸め対策を実装。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を計算。
    - pandas など外部大規模依存を避け、標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キー等の機密情報は Settings 経由で管理する前提。自動 .env ロードはテスト等のため環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可。

---

## 運用 / マイグレーション ノート（運用者向け）
- 必要な DB テーブル（主なもの）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - 各モジュールはこれらのテーブル構造に依存するため、初回導入時はスキーマ準備が必要です。

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（ai.score_news / regime_detector.execution の実行時に必要）
  - 任意: KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH

- デフォルト値
  - KABU_API_BASE_URL: http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

- OpenAI 呼び出し
  - gpt-4o-mini を利用（JSON Mode）。API エラー時はリトライ＆フェイルセーフ（スコア 0.0、あるいはチャンクスキップ）を行います。
  - テスト容易性のため内部 API 呼び出し関数をモック可能（unittest.mock.patch で差し替え）。

- ルックアヘッドバイアス対策
  - AI スコアやレジーム判定で datetime.today()/date.today() を直接参照せず target_date ベースでウィンドウを計算する設計。

- ロギング / エラー処理
  - 各処理は情報ログ・警告ログを出力し、DB 書き込みは基本的にトランザクションで冪等性を維持。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

---

この CHANGELOG はソースコードから推測して作成しています。機能の詳細や運用上の注意は README や該当モジュールのドキュメントを参照してください。
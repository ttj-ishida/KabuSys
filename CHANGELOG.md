# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはリポジトリのコードベースから推測して作成した初回の変更履歴です。

現在日付: 2026-03-29

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買プラットフォームのコア機能群を実装しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, monitoring, strategy, execution 等を想定）を公開。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出機能: .git または pyproject.toml を起点にルートを探索（CWD 非依存）。
  - .env パーサーを実装（コメント、export プレフィックス、クォートとエスケープに対応）。
  - .env 自動ロード順序: OS 環境変数 > .env.local > .env。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI: ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとの記事テキストを作成し、OpenAI（gpt-4o-mini）に対してバッチで JSON Mode を用いたセンチメントスコアリングを実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（内部的に UTC naive datetime に変換）。
  - バッチ/トークン肥大化対策: 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事、3000 文字にトリム。
  - 再試行/バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数的バックオフでリトライ（最大 _MAX_RETRIES）。
  - レスポンス検証および堅牢な JSON 抽出ロジック（余計な文字列混入への対応）。
  - DuckDB への安全な書き込み処理: 部分失敗時に既存スコアを保護するため、対象コードに絞って DELETE → INSERT を実行。DuckDB の executemany の空リスト制約に配慮。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 件）。
  - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - レジームスコアはクリップ処理後、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみを使用。

- データ: カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー管理ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - market_calendar テーブルの有無に応じて DB 値優先、未登録日は曜日ベース（週末除外）でフォールバック。
  - 夜間バッチ job (calendar_update_job) により J-Quants API から差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を行う。
  - 最大探索日数や健全性チェック（将来日付の閾値）などの安全策を導入。

- データ: ETL パイプライン（kabusys.data.pipeline / etl）
  - ETLResult データクラスを公開し、ETL 実行結果の集約（取得数・保存数・品質問題・エラー）を提供。
  - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールを利用）。
  - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

- 研究 (research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR、流動性指標等を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 入力データは prices_daily / raw_financials のみ。外部 API へはアクセスしない。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランキング（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと SQL（DuckDB）で実装。

- テスト・拡張性への配慮
  - OpenAI 呼び出し点（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）をユニットテスト用に patch/差し替え可能に実装。
  - 設定読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト容易化）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 注意点 / 既知の制約
- OpenAI API キー（OPENAI_API_KEY）未設定時は score_news・score_regime が ValueError を送出します。
- OpenAI API 呼び出し失敗時は多くの処理でフェイルセーフとしてスコア 0.0 を採用し、処理を継続します（例: macro_sentiment=0.0, スキップして次チャンクへ）。
- DuckDB の executemany は空リストを受け付けないバージョン挙動に対する回避処理が含まれる（空チェック済み）。
- market_calendar が未登録の場合、休日判定は単純に土日を非営業日とするフォールバックを使用する。
- 現バージョンでは PBR や配当利回り等のファクターは未実装。
- 一部モジュール（例: kabusys.data.jquants_client, kabusys.data.quality, monitoring, strategy, execution）は本ログ作成対象コードに含まれているものの、ここに掲載された実装依存部分（関数呼び出し/インターフェース）に依存するため、実際の動作にはそれらの実装が必要です。

### 必要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (score_news / score_regime 実行時に必須)
- KABUSYS_ENV (development / paper_trading / live、デフォルト development)
- LOG_LEVEL (デフォルト INFO)

---

この CHANGELOG は、提供されたソースコード（src/kabusys 以下）から機能と設計方針を推測して作成しています。実際のリリースノートや運用ドキュメント作成時は、追加の変更点・依存関係・互換性情報を反映してください。
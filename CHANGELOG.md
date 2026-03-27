# Changelog

すべての重要な変更点をここに記録します。（Keep a Changelog 準拠）  
このプロジェクトの初回リリースをまとめています。

フォーマットの解説: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買/リサーチ用のコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 基本パッケージ
  - kabusys パッケージの公開（__version__ = 0.1.0）。パッケージインターフェースは data, strategy, execution, monitoring を想定。

- 設定管理 (kabusys.config)
  - .env 自動読み込み実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース直前の # をコメント扱い）に対応。
  - 環境変数保護: OS 環境変数は protected として .env による上書きを防止。
  - Settings クラスを提供し、用途別のプロパティを公開:
    - J-Quants / kabu ステーション / Slack トークンやチャネル等を必須取得（未設定時は ValueError）。
    - duckdb, sqlite のデフォルトパス設定。
    - KABUSYS_ENV / LOG_LEVEL の検証と is_live / is_paper / is_dev 判定。

- データ基盤（DuckDB ベース）
  - ETL パイプラインの型表現 ETLResult（kabusys.data.pipeline.ETLResult を re-export）。
  - pipeline モジュールに差分取得 / 保存 / 品質チェックのためのユーティリティを実装（バックフィル日数や最大探索等のポリシーを含む）。
  - calendar_management による市場カレンダー管理:
    - market_calendar に基づく営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API からの差分取得→冪等保存（バックフィル・健全性チェック付き）。

- AI（OpenAI 統合）機能
  - ニュースセンチメント (kabusys.ai.news_nlp):
    - score_news(conn, target_date, api_key=None): RAW ニュースを銘柄別に集約し、gpt-4o-mini（JSON mode）でセンチメントを取得して ai_scores テーブルへ保存。
    - 処理特徴: JST ベースのニュースウィンドウ計算、1銘柄あたり記事数・文字数トリム、銘柄をチャンク（最大 20）でバッチ処理、429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ。
    - レスポンス検証とクリッピング（±1.0）、部分失敗時でも既存スコアを保護するため対象コードのみ DELETE→INSERT（冪等性確保）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ保存。
    - LLM 呼び出しは独立実装、失敗時は macro_sentiment=0.0 のフェイルセーフ、リトライロジック内蔵。
    - レジームスコアのクリッピングとラベリング（bull / neutral / bear）、DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。

- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の SQL 実装。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: PER, ROE の算出（raw_financials から最新財務を取得）。
    - 全て DuckDB SQL を主体に実装し、過不足データに対する None 処理を実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的なクエリ。
    - calc_ic: スピアマン（ランク相関）による IC 計算（同順位は平均ランク処理）。
    - rank, factor_summary: ランク化と基本統計量サマリー。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### セキュリティ (Security)
- .env 読み込みで OS 環境変数を保護（.env により重要な OS 環境変数が誤って上書きされない）。

### 備考 / 設計上の注意点
- ルックアヘッドバイアス対策: score_news / score_regime 等は内部で datetime.today() / date.today() を直接参照せず、明示的な target_date 引数を用いる設計。
- DuckDB を一次的な分析・保存ストアとして利用（テーブル名: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等を前提）。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode（response_format={"type": "json_object"}）を利用する想定。レスポンスパースに堅牢な防御を備える（余分な前後テキストを除去して JSON を抽出する等）。
- 部分的な外部 API 失敗は例外で処理を停止するのではなく、フェイルセーフ（neutral/0.0 スコアなど）で継続する設計を採用。
- テスト容易性: OpenAI への低レベル呼び出し関数はモジュールごとに差し替え可能（unittest.mock.patch を想定）。

---

もし必要であれば、各関数（score_news, score_regime, calc_momentum など）の使用例や、マイグレーション／セットアップ手順（必要な環境変数一覧とデフォルト値）を別途追加で作成します。どの情報を優先して追加しますか？
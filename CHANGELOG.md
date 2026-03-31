# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」準拠で記載しています。セマンティックバージョニングを採用しています。  

## [Unreleased]

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージの基本構成
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data, research, ai, execution, monitoring（__all__ によりエクスポート）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ロード実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない動作。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメントの扱い（クォートなしは '#' の前がスペース/タブの場合にコメントと判定）等に対応。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level）等のプロパティを定義。
    - env と log_level の値チェック（許容値のバリデーション）。
    - ファイルパスは Path オブジェクトで返却（expanduser 対応）。

- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None) を提供。
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウを計算（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数でトリム）。
    - 最大 _BATCH_SIZE（20）銘柄ずつ OpenAI (gpt-4o-mini) にバッチ送信して銘柄別センチメントを取得。
    - レスポンス検証（JSON の整形抽出、results 配列、code/score の妥当性チェック）。
    - スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護。
    - テスト支援: _call_openai_api を patch して差し替え可能。
  - calc_news_window(target_date) を公開（UTC naive datetime を返す）。
  - 空レスポンスや API エラー時は安全にスキップし、処理継続（フェイルセーフ）。

- 市場レジーム判定（AI） (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None) を提供。
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI により JSON で macro_sentiment を取得。
    - LLM 呼び出しはリトライ（指数バックオフ）を実装、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト支援: _call_openai_api の差し替えが可能。
  - マクロキーワード一覧、モデル名、リトライロジック等を定義。

- 研究用ファクター群 (src/kabusys/research/*.py)
  - calc_momentum(conn, target_date)
    - 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
  - calc_volatility(conn, target_date)
    - 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
  - calc_value(conn, target_date)
    - raw_financials から直近決算を取得し PER、ROE を計算（EPS 0 や欠損時は None）。
    - PBR・配当利回りは現バージョンでは未実装（注記あり）。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary（統計量）、rank（平均ランク処理）を提供。
  - research パッケージの __init__ により主要関数を再エクスポート。

- データプラットフォーム（Data） (src/kabusys/data/*.py)
  - calendar_management.py
    - JPX 市場カレンダー（market_calendar）を扱うユーティリティ。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録がない場合は曜日ベースのフォールバック（週末非営業）を使用。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得し market_calendar を冪等に更新。バックフィルと健全性チェックを実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを導入（ETL の実行結果、品質問題、エラー等を集約）。
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェックの設計に沿った処理を実装するための土台を提供。
    - DuckDB のバージョン依存（executemany の空リスト制約）に配慮した実装を反映。

- いくつかのユーティリティと設計上の配慮
  - DuckDB の日付/型取り扱いに関する変換ユーティリティ（_to_date 等）。
  - 各モジュールで「ルックアヘッドバイアス防止」のために datetime.today()/date.today() を直接参照しない方針を採用（target_date を明示）。
  - LLM 呼び出しは冪長性（リトライ、5xx の扱い）・安全フォールバック（macro_sentiment=0.0、空レスポンスのスキップ）を実装。
  - OpenAI 呼び出しのレスポンスパースで柔軟性を持たせ、JSON mode でも前後の余計なテキストを丸めて抽出するロバストネスを追加。
  - テストしやすさのため、内部 API 呼び出し関数（_call_openai_api 等）を patch 可能に設計。

### 変更 (Changed)
- （初版）設計方針・実装注記をソース内ドキュメントとして多数追加:
  - 各モジュールで想定される DB テーブル、参照制約、フォールバック、エラー処理方針などを詳細に明記。
  - リトライ挙動や閾値、各定数（バッチサイズ、ウィンドウ時間、閾値など）をソース内定数として整理。

### 修正 (Fixed)
- 初期リリースでは主に実装完了のため「修正」はなし。  
  （ただし、DuckDB 0.10 における executemany の空パラメータ制約に対する回避ロジックを組み込み、部分失敗時の既存データ保護ロジックを実装しています。）

### 注意事項 (Notes)
- OpenAI API を利用するため、実行時に OPENAI_API_KEY（もしくは各関数引数経由での api_key 指定）が必須です。未設定時は ValueError を発生させます。
- .env の自動読み込みはプロジェクトルートが特定できない場合スキップされます（パッケージ配布後の安全仕様）。
- PBR や配当利回りなどの一部バリューファクターは現バージョンで未実装です（calc_value の docstring に注記あり）。
- DuckDB を利用する実装のため、環境に応じた DuckDB バージョン差異に注意してください（一部回避処理を実装済み）。
- jquants_client や外部 API 呼び出しに失敗した場合は、ログを残して安全にスキップする設計になっています。

### 依存関係（実行時）
- duckdb
- openai（OpenAI Python SDK、chat completions を使用）
- 外部クライアント: jquants_client（Data モジュールから使用）

---
今後のリリースでは、テストカバレッジ、ドキュメント整備（ユーザー向け設定例・ETL 実行手順）、および運用監視／発注周りの実装（execution / monitoring モジュールの詳細）を強化予定です。
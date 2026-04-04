# CHANGELOG

すべての注目すべき変更履歴を記録します。  
このファイルは Keep a Changelog のスタイルに準拠しています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョン管理方針: SemVer 準拠

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-04
初回リリース — 基本的なデータ基盤、リサーチ、AI ベースのニュースセンチメント、カレンダー/ETL ユーティリティを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化とバージョニング（__version__ = 0.1.0）。
  - パッケージ公開 API の簡易定義（data, strategy, execution, monitoring を __all__ に登録）。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 環境変数自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - protected 引数による OS 環境変数の上書き防止をサポート。
  - Settings クラスを実装し、環境変数からの設定取得をラップ（J-Quants, kabuAPI, LINE, DB パス, 監視パラメータ等）。
    - 必須環境変数未設定時は明示的に ValueError を発生させる _require を提供。
    - KABUSYS_ENV の許容値: development / paper_trading / live。LOG_LEVEL の許容値: DEBUG/INFO/WARNING/ERROR/CRITICAL。
    - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 監視用パラメータ（PID ファイル、kill flag、リソース閾値等）を設定可能。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols から指定ウィンドウのニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime を使用）。
    - バッチ処理: 1 回の API コールで最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたりの最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装し、プロンプト肥大化を防止。
    - JSON Mode を期待し厳密な JSON を検証。JSON 前後の余計な文字列対応（最外の {} を抽出してパース）。
    - レスポンス検証: results 配列、code の照合、score の数値変換、スコアの ±1.0 クリップ。
    - 再試行ロジック: 429 (RateLimit), 接続エラー, タイムアウト, 5xx をエクスポネンシャルバックオフでリトライ。
    - フェイルセーフ: API エラー時はそのチャンクをスキップして処理を継続（例外を投げずにログ出力）。
    - データベース書き込みは冪等的に実施（対象コードのみ DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し部分を _call_openai_api で分離しパッチ可能。
  - レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei-225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）の合成で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のみを参照してルックアヘッドバイアスを防止。
    - マクロ記事はキーワードベースで抽出（_MACRO_KEYWORDS）、最大 20 記事。
    - OpenAI（gpt-4o-mini）を使ったマクロセンチメント評価を実装。API が失敗した場合は 0.0 をフォールバック（警告ログ）。
    - 冪等な DB 書き込み処理を実装（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ（Data Platform）モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定関数群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータが無い場合は曜日ベース（週末を休場）でフォールバック。
    - next/prev/get_trading_days の探索は最大 _MAX_SEARCH_DAYS（安全対策）で制限。
    - calendar_update_job を実装し J-Quants API（jquants_client）から差分取得・保存（バックフィルと健全性チェック付き）。
  - ETL パイプライン (pipeline)
    - ETLResult dataclass を公開し、ETL 実行結果の集約（取得/保存件数、品質問題、エラーログ等）を扱えるように実装。
    - 差分更新、バックフィル、品質チェックの考え方をコードに反映（jquants_client, quality との連携を想定）。
    - _get_max_date / _table_exists 等のユーティリティを実装（DuckDB ベース）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB を使った SQL + Python ハイブリッド実装。対象テーブル: prices_daily, raw_financials。
    - データ不足時の扱い（None を返す）やログ出力を含む。
  - feature_exploration
    - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズンは最大 252 営業日までの検証あり）。
    - IC（Information Coefficient）計算（スピアマン ρ の実装）、ランク変換ユーティリティ rank、ファクター統計 summary（count/mean/std/min/max/median）。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装を方針とする。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ / オペレーションに関する注意
- OpenAI 関連機能を使うには OPENAI_API_KEY が必要（api_key 引数で注入可）。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN、kabu ステーション操作には KABU_API_PASSWORD 等の環境変数が必要。
- .env 自動読み込みはデフォルトで有効。テストや CI で無効化する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB の書き込みは冪等化を心がけているが、本番運用前にバックアップや監査ログの設定を推奨します。

### 開発者向けメモ / 実装上の設計方針（要約）
- ルックアヘッドバイアス防止: datetime.today()/date.today() をアルゴリズム内部で参照しない設計（すべて target_date に依存）。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）障害時はできる限り処理を継続し、影響範囲を局所化する（例: マクロセンチメント失敗時は 0.0 フォールバック）。
- テスト容易性: OpenAI 呼び出し部分を内部関数で切り出しモック可能としている。
- DuckDB を中心に据えたデータ処理。DuckDB の executemany の空リスト扱い等の挙動差を考慮した実装。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの詳細実装とテスト。
- ai モデルのプロンプト改善や多言語対応、モデル切替の設定化。
- 運用向けのロギング、メトリクス、アラート連携強化。

フィードバックや不具合報告は issue を作成してください。
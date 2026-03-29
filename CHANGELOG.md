# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載しています。  
このファイルはリポジトリのコードベースから推測して作成された変更履歴です。

## [Unreleased]

（現時点のソースに基づく初期リリース情報は下段の 0.1.0 を参照してください。今後の変更はここに追記してください。）

---

## [0.1.0] - 2026-03-29

初期公開リリース。日本株自動売買システムのコアユーティリティ群を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化（バージョン: 0.1.0）。
  - パブリック API: data, strategy, execution, monitoring モジュールを __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env ファイルのパース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを追加し、アプリ設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 設定が必須の環境変数未設定時に明確な ValueError を発生させる _require() を実装。

- AI: ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news / news_symbols テーブルのニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメントスコアを算出。
  - タイムウィンドウ計算（JST ベース、前日 15:00 ～ 当日 08:30 を UTC に変換）を実装（calc_news_window）。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄／コール）、1銘柄あたりの最大記事数/文字数制限（デフォルト: 10 件／3000 文字）を実装。
  - レスポンスのバリデーションとスコアクリップ（±1.0）を実装。
  - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ、非致命エラー時はスキップして処理継続。
  - DuckDB への書き込みは冪等（DELETE → INSERT）で実行し、部分失敗時に既存スコアを保護。
  - テスト用に _call_openai_api をパッチ差し替え可能（unittest.mock.patch 想定）。

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
  - マクロニュース抽出でのキーワードリスト、LLM 呼び出しのリトライ・フォールバック（API 失敗時 macro_sentiment = 0.0）を実装。
  - レジーム判定のスコア合成ロジックと閾値（BULL/BEAR）を実装。
  - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に行い、失敗時は ROLLBACK を行う。

- データ処理 / ETL (kabusys.data.pipeline, etl, jquants_client 連携想定)
  - ETLResult dataclass を追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を表現。
  - 差分更新、バックフィル、品質チェックの方針を実装するための基盤を追加（J-Quants クライアント呼び出しは jquants_client を通じて行う想定）。
  - DuckDB 上での最終取得日取得ユーティリティ、テーブル存在チェック等を実装。

- データ: マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を前提とした営業日判定ユーティリティを追加:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB にカレンダーがない場合は曜日ベース（土日休）でフォールバック。
  - calendar_update_job を実装し、J-Quants からの差分取得 → 保存（バックフィル含む）を行う。健全性チェックや例外処理を含む。

- 研究用ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位を平均ランクで扱うランク関数。
  - data.stats から zscore_normalize を再エクスポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 注意点 / マイグレーション (Notes / Migration)
- 必須環境変数:
  - OPENAI_API_KEY（news_nlp / regime_detector の呼び出し時に必要）
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD（kabu_api と接続する場合）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）
- .env の自動ロードはプロジェクトルートの検出が成功した場合のみ行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への複数行 INSERT/DELETE は executemany を利用します。DuckDB 0.10 系での空リストバインドに注意（空の executemany を回避するガードあり）。
- OpenAI API 呼び出しは JSON mode を期待しており、LLM の応答検証や余分テキストのトリムを行っていますが、レスポンスフォーマットの変化には注意してください。

### セキュリティ (Security)
- （初期リリースのため該当なし）

---

参考: この CHANGELOG はソースコードの内容とコメントから推測して作成されています。実際のリリースノート作成時は、変更内容・日付・著者・関連 Issue/PR を合わせて更新してください。
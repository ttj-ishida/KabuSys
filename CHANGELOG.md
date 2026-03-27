# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初回公開リリースを記録しています。

全般的な方針:
- 日時の取得において datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計（ルックアヘッドバイアス防止）。
- DuckDB を主要なローカル分析DBとして使用。DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT / ON CONFLICT 等）。
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、レスポンスの堅牢なバリデーションとエクスポネンシャルバックオフ方式のリトライを実装。
- API 失敗時はフェイルセーフ（例: LLM 失敗なら中立スコア 0.0 を使用）で処理継続。

## [0.1.0] - 2026-03-27

### Added
- パッケージ基礎
  - kabusys パッケージ初期構成を追加。公開 API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（__all__ を定義）。
  - バージョン: 0.1.0。

- 設定管理 (kabusys.config)
  - 環境変数 / .env ファイルを読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動読み込み（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local (override=True) > .env (override=False)。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
    - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - 既存 OS 環境変数は protected として上書きされない。
  - Settings クラスを公開（settings）。主要な必須環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の補助プロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols をもとに銘柄別センチメントを計算し ai_scores テーブルへ書き込む score_news 関数を実装。
  - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部では UTC naive datetime に変換して扱う）。
  - 1銘柄あたり最大記事数・最大文字数のトリム、バッチサイズ（最大 20 銘柄）の API 呼び出し。
  - OpenAI 呼び出しは JSON モードで行い、レスポンスの検証（results 配列、code/score 型チェック、score の有限性、既知コードのみ採用）を実装。
  - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。その他エラーはスキップして処理継続。
  - API 呼び出し部分はテスト容易性のため差し替え可能（unittest.mock.patch 対応）。
  - 成功時は ai_scores テーブルに対して該当コードのみ DELETE → INSERT を実行し、部分失敗時に既存スコアを保護。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定する score_regime 関数を実装。
  - prices_daily から過去データを安全に取得する実装（target_date 未満のデータのみ使用、ルックアヘッド防止）。
  - マクロニュースは kabusys.ai.news_nlp の calc_news_window を用いて取得し、OpenAI で評価（gpt-4o-mini）。
  - OpenAI の失敗時には macro_sentiment=0.0 をフェイルセーフとして使用。
  - DB 書き込みは冪等性を保つ（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- 研究用ファクター群（kabusys.research）
  - factor_research モジュールを追加。以下の関数を提供:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離率（ma200_dev）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率など
    - calc_value: PER (price / EPS)、ROE（raw_financials から最新財務を取得）
  - feature_exploration モジュールを追加。以下を提供:
    - calc_forward_returns: 複数ホライズンの将来リターン計算（デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算（不足データ・同値を考慮）
    - factor_summary: カラムごとの count/mean/std/min/max/median
    - rank: 平均ランク（同順位は平均ランク）計算
  - zscore_normalize は kabusys.data.stats から再エクスポート（__init__）。

- データプラットフォーム（kabusys.data）
  - calendar_management: market_calendar 管理と営業日判定ユーティリティを実装:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - データが無い場合は曜日ベース（週末除外）でフォールバック。
    - 最大探索日数を設定し無限ループを防止。
    - calendar_update_job: J-Quants API からカレンダーを差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline: ETL パイプラインのための ETLResult データクラスを実装（kabusys.data.etl で再エクスポート）。
    - ETLResult は取得/保存件数、品質チェック問題、エラー一覧などを保持し、to_dict によりシリアライズ可能。
  - jquants_client と quality 関連の呼び出しを想定した設計（実際のクライアントは別モジュールで注入）。

### Changed
- 初回リリースのため該当なし。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 必須 API キー（OpenAI, J-Quants 等）は環境変数で管理するよう設計。設定未提供時は ValueError を送出して明示的に失敗する箇所あり（score_news, score_regime 等）。
- .env ファイル読み込みはデフォルトで有効だが、テスト環境等で KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化できる。

### Notes / Implementation Details
- OpenAI 呼び出しは gpt-4o-mini を使用し、response_format={"type": "json_object"} を指定して厳密な JSON を期待する実装。ただし実運用で余計なテキストが混ざる場合に備え、JSON 抽出ロジックを含む。
- LLM や外部 API の障害時は可能な限り例外を上位へ伝播させず、部分的に中立値やスキップを行う（フェイルセーフ）。ただし DB 書き込み時の例外は上位へ伝播（ROLLBACK の上で再送出）。
- DuckDB に対する executemany の互換性（空リスト禁止など）を考慮してガードを入れている。
- 多くの内部関数（_call_openai_api 等）はテストで差し替え可能に設計（モック化を想定）。

---

今後の予定（例）
- strategy / execution / monitoring の具体的実装公開。
- J-Quants クライアントの実装と ETL の本格導入、CI 用の統合テストの追加。
- モデルやプロンプトの改善、ログ・メトリクスの充実、監視アラート連携。

もし CHANGELOG に追記して欲しい点（例: リリース日を別日にしたい、より詳細な項目分割、特定ファイルへの注記など）があれば教えてください。
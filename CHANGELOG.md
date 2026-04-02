Keep a Changelog に準拠した形式で、このコードベースの初回リリース向け CHANGELOG を日本語で作成しました。コードから推測できる追加機能、挙動、設計上の注意点を記載しています。

CHANGELOG.md
=============
すべての注目すべき変更をこのファイルで管理します。  
形式は Keep a Changelog に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-02
--------------------

Added
-----
- パッケージ初期リリース: kabusys v0.1.0
  - 概要: 日本株自動売買／研究プラットフォームの基盤ライブラリ。
  - パッケージエントリポイント: src/kabusys/__init__.py にて version と公開モジュールを定義。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイル / 環境変数からの自動読み込みを実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き防止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ: export 記法、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスでアプリ設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL（検証済み値）
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとの記事テキストを生成し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime として扱う calc_news_window 実装）。
  - バッチ処理: 最大 _BATCH_SIZE（20）銘柄を 1 API コールで処理。
  - 1銘柄あたり最大記事数・文字数制限: _MAX_ARTICLES_PER_STOCK（10）、_MAX_CHARS_PER_STOCK（3000）でトリム。
  - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、非リトライ系エラーは該当チャンクをスキップして継続。
  - レスポンス検証: JSON パース回復策（最外の {} 抽出）、"results" 配列構造・型チェック、未知コードの無視、スコアを ±1.0 にクリップ。
  - 書き込み: 成功した銘柄コードのみ ai_scores テーブルへ DELETE → INSERT の冪等書き込み（部分失敗時に既存スコアを保護）。
  - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - テスト容易性: OpenAI 呼び出しを _call_openai_api で抽象化して差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - マクロ記事抽出は news テーブルからキーワードマッチで行い、最大件数制限あり。
  - OpenAI 呼び出しは別実装（news_nlp と共有しない）で、JSON Mode を使い {"macro_sentiment": <score>} を期待。
  - フェイルセーフ: 記事が無い or API 失敗時は macro_sentiment = 0.0 を採用。
  - 書き込み: market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT による冪等書き込み。
  - public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- データプラットフォーム関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar テーブルの有無に応じて DB 値優先、未登録日は曜日（週末）フォールバックを採用。
    - calendar_update_job で J-Quants API から差分を取得し、バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（未来日付の異常検出）を行い冪等に保存。
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分更新、backfill、品質チェック（quality モジュールと連携）を想定した設計。
    - jquants_client を経由した保存処理の呼び出し想定。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ / ファクター群（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を提供
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（データ不足時は None を返す設計）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）。
    - すべて DuckDB 上で SQL を使って計算、prices_daily / raw_financials のみ参照（発注 API 等へはアクセスしない）。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
    - 将来リターン（複数ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）をランク相関で計算、サンプル数が不足すれば None を返す。
    - 統計サマリー（count/mean/std/min/max/median）を純標準ライブラリで提供。
    - rank 実装は同順位の平均ランク化、丸めによる ties 処理を含む。

- 共通設計注意点（全体）
  - ルックアヘッドバイアス対策: 各種スコアリング / 判定で datetime.today() / date.today() を参照しない設計。target_date ベースで過去データのみ参照する。
  - DuckDB をデータ層に採用（関数群は DuckDB 接続を引数に取る）。
  - OpenAI 依存機能は API キー注入を引数で受け取り、環境変数 OPENAI_API_KEY も利用可能。テスト用に API 呼出箇所を差し替え可能。
  - 多くの処理で冪等性・部分失敗時の安全性（部分書き込み保護）を重視している。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Deprecated
----------
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Security
--------
- OpenAI / J-Quants 等外部 API キーは環境変数で扱う設計。機密情報の取り扱いは .env に依存する場合は注意（.env.local の優先、OS 環境変数の保護などの仕組みあり）。

Notes / 既知の設計上の注意
-------------------------
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を想定しているため、API 仕様変更やレスポンス形式の変化に注意。
- DuckDB の executemany に関する挙動（空リストの扱い）に配慮して処理が実装されている（空の params を渡さないガードあり）。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存。これらのクライアント実装とエラー挙動によりジョブ結果が変わる可能性あり。
- 半自動的に .env ファイルを読み込むが、CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

作者ノート（推測）
----------------
- 本リリースは「データプラットフォーム」「AI を使ったニュースセンチメント」「因子計算／リサーチ」の基盤機能を揃えた初期バージョンと推測されます。今後は取引執行（execution）や監視（monitoring）の実装拡充、テスト / ドキュメントの追加、API 仕様に合わせた微調整が想定されます。

--------  
タグ:
- バージョン: 0.1.0
- 日付: 2026-04-02

（必要であれば、各モジュールの変更履歴をさらに細分化して追記します。どの粒度で記載したいか指示してください。）
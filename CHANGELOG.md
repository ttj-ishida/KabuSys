CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

0.1.0 - 2026-03-26
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)。
- 基本パッケージメタ情報:
  - src/kabusys/__init__.py に __version__=0.1.0、公開サブパッケージ一覧を追加。

- 環境変数・設定管理:
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
    - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等を正しく処理。
    - ロード優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - is_live / is_paper / is_dev のユーティリティ

- AI（ニュースNLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）でバッチ評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチング、チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限（トリム）を実装。
    - OpenAI 呼び出しは JSON Mode を期待し、レスポンスを厳密にバリデートして ±1.0 にクリップ。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。その他のエラーはスキップして継続（フェイルセーフ）。
    - スコア書き込みは冪等性を考慮して DELETE → INSERT（対象コードのみ）を実行し、部分失敗による既存スコア消失を回避。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。APIキーは引数優先、なければ環境変数 OPENAI_API_KEY を参照。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは news_nlp のウィンドウ集約関数(calc_news_window)を利用して raw_news をフィルタし、OpenAI（gpt-4o-mini）で評価。
    - API 呼び出しの堅牢化（リトライ・5xx ハンドリング・JSON パース失敗時のフォールバック macro_sentiment=0.0）。
    - レジーム算出式と閾値実装、market_regime テーブルへの冪等書き込みを実装。
    - 公開 API: score_regime(conn, target_date, api_key=None)。APIキー解決は score_news と同様。

- データプラットフォーム関連:
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が未取得の場合は曜日（土日）ベースでフォールバックする設計。DB 登録値があればそれを優先。
    - カレンダー夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアントを使って差分取得・冪等保存（バックフィルや健全性チェック含む）。
  - src/kabusys/data/pipeline.py
    - ETL パイプライン用ユーティリティと方針を実装（差分取得、保存、品質チェックの骨子）。
    - ETLResult データクラスを提供（target_date, fetched/saved counts, quality_issues, errors 等）。to_dict による品質問題の整形をサポート。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディング日調整等。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- リサーチ（ファクター計算 / 特徴量探索）:
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー関連ファクター計算を実装:
      - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（必要行数未満は None）
      - calc_value(conn, target_date): per, roe を raw_financials と prices_daily から計算
    - DuckDB を用いた SQL 中心の実装（外部APIや本番発注にはアクセスしない設計）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ランク相関）
    - ランク化ユーティリティ: rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
  - src/kabusys/research/__init__.py
    - 主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- パッケージ構成:
  - ai/__init__.py、research/__init__.py、data/etl.py 等、各モジュールのエクスポートを整備。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の重要点（ドキュメント的補足）
- ルックアヘッドバイアス防止:
  - いずれの分析/スコアリング関数も datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計としています。
  - DB クエリは target_date 未満 / 以前など明示的な排他条件で過去データのみ参照します。
- フェイルセーフ設計:
  - API 呼び出し失敗時は可能な限り局所的にフォールバック（例: macro_sentiment=0.0、スコア取得チャンクはスキップ）し、例外を全体に波及させないようにしています。ただし DB 書き込み失敗等の重大エラーは上位に伝播します。
- 冪等性:
  - ai_scores / market_regime / market_calendar への書き込みは既存行を削除してから挿入する等、部分的な再実行や再取得に耐える形で実装しています。
- OpenAI 連携:
  - gpt-4o-mini を利用する前提のプロンプトと JSON Mode でのレスポンス処理を採用しています。
  - API キーは関数引数で注入可能（テスト容易性）で、未指定時は環境変数 OPENAI_API_KEY を参照します。
- 環境変数の必須チェック:
  - Settings の必須プロパティは未設定時に ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

Required / Recommended environment variables
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (任意: DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (自動 .env ロードを無効化する場合に 1 を設定)

Security
- （初回リリースのため該当なし）

Acknowledgements
- このリリースでは内部設計方針やフェイルセーフ・冪等性・ルックアヘッド防止等に重点を置いて実装しています。今後のリリースではテストカバレッジ拡充、ドキュメント追加、API クライアントの抽象化やメトリクス収集などを予定しています。
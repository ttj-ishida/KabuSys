Keep a Changelog
=================

この CHANGELOG は Keep a Changelog の形式に従っています。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージの公開モジュールとして data, strategy, execution, monitoring を意図的にエクスポート（各サブパッケージは今後実装/拡張）。
- 環境設定/ロード機能:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - export KEY=val 形式、クォート・エスケープ、インラインコメントの取り扱い、無効行スキップ等の堅牢な .env パーサ実装。
    - Settings クラスで各種必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や DB パス（DUCKDB_PATH, SQLITE_PATH）、実行環境（KABUSYS_ENV）やログレベルを取得・検証。
    - OS 環境変数を保護する protected 機能（.env.local の上書き処理時など）。
- AI（NLP）モジュール:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）でバッチ評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数／文字数制限、レスポンスの厳密なバリデーション（JSON抽出、results 配列・型検証、スコアの数値化とクリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ戦略、API 失敗はフォールバック（例外を投げずスキップ）でフェイルセーフに設計。
    - DuckDB の executemany に関する互換性配慮（空リスト送信を避けるためのチェック）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出、OpenAI（gpt-4o-mini）呼び出し、JSONパース、リトライ/バックオフ、API失敗時の安全なフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB の market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
- データ（Data Platform）モジュール:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）ヘルパーを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API（jquants_client を通じて）から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（将来日付の異常検出）に対応。
  - src/kabusys/data/pipeline.py
    - ETL パイプライン用の ETLResult データクラスを提供（取得数・保存数・品質チェック結果・エラー集約など）。
    - 差分更新・バックフィル・品質チェック等の設計方針に基づくユーティリティを実装（内部ユーティリティ関数群を含む）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートして public API を整理。
- 研究（Research）モジュール:
  - src/kabusys/research/factor_research.py
    - Momentum（1/3/6M、ma200 乖離）、Volatility（20日 ATR、相対ATR）、Value（PER、ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を多用し、高速に集計・窓関数を用いた実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず、標準ライブラリと SQL で完結する設計。
  - src/kabusys/research/__init__.py に主要 API をエクスポート（zscore_normalize は kabusys.data.stats からの再利用を想定）。
- 共通設計ポリシー（ドキュメント化・実装に反映）
  - ルックアヘッド（先読み）バイアス防止: 各モジュールで datetime.today()/date.today() を直接参照しない、target_date ベースの計算を採用。
  - API 呼び出しに対する堅牢なフォールバック（失敗時の既定値）とリトライ/バックオフ戦略。
  - DB 書き込みは冪等性を意識した実装（DELETE→INSERT など）。DuckDB 互換性への配慮（executemany 空リスト回避など）。
  - OpenAI の JSON Mode を使用したレスポンス厳密化と、応答の復元ロジック（前後余計なテキストが混ざる場合の {} 抽出）を採用。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- jquants_client 等の外部クライアントモジュールは参照されるが本差分には実装が含まれないため、実行環境ではそれらの依存実装が必要。
- OpenAI 呼び出しは gpt-4o-mini を想定。APIキーの注入は関数引数（api_key）または環境変数 OPENAI_API_KEY を想定しており、テスト容易性のため引数注入が可能。
- SQLite / DuckDB のテーブルスキーマや外部データの準備が前提（raw_news, prices_daily, raw_financials, market_calendar, ai_scores, news_symbols, market_regime 等）。

References
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース手順に従って更新してください。
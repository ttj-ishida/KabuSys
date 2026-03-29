Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
このプロジェクトはセマンティック バージョニングを採用しています。

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期公開: kabusys v0.1.0
  - src/kabusys/__init__.py により public API をエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサは export プレフィックスやシングル/ダブルクォート、エスケープシーケンス、行内コメントの扱いに対応。
    - _load_env_file の override / protected オプションにより OS 環境変数を保護しつつ .env.local で上書き可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
- AI（ニュース NLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - チャンク単位（デフォルト最大 20 銘柄）でのバッチ呼び出し、記事数・文字数トリム（最大記事数/最大文字数）を導入。
    - JSON モードのレスポンス検証、結果のクリップ（±1.0）、リトライ（429/ネットワーク/5xx は指数バックオフ）を実装。
    - DuckDB との整合性考慮（executemany に空リストを渡さない等）で ai_scores テーブルへ冪等的に書き込み。
    - calc_news_window により JST 基準のウィンドウ（前日 15:00 JST ～ 当日 08:30 JST、UTC へ変換）を厳密に算出。ルックアヘッドバイアスを防止する設計。
    - テスト用に内部の _call_openai_api を patch しやすい実装（モジュール内で独立実装）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードで raw_news をフィルタリングし、最大記事数を制限して LLM に渡す。API エラー時はフェイルセーフで macro_sentiment=0.0 として継続。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、幾度かのリトライ・指数バックオフ・5xx の扱いを考慮。
    - market_regime テーブルへ冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
- Research（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離（ma200_dev）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足場合は None を返し、営業日ベースのウィンドウ設計やスキャン範囲バッファを考慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 複数ホライズンに対応、ホライズンバリデーションあり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を実装。サンプル数不足時は None を返す。
    - ランク変換時の ties（同順位）に対して平均ランクを採用し、浮動小数丸め誤差対策を実装。
    - factor_summary により基本統計量（count/mean/std/min/max/median）を計算。
    - research パッケージ __all__ を通じて主要関数を再エクスポート。
- Data（カレンダー管理 / ETL / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。探索上限（_MAX_SEARCH_DAYS）により無限ループを防止。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新する処理を実装。バックフィル・健全性チェックを導入。
  - src/kabusys/data/pipeline.py / etl.py
    - ETL の高レベル設計を実装。差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール経由）のワークフローを提供。
    - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーの集約とシリアライズ機能（to_dict）を提供。
    - DuckDB テーブル存在チェック・最終取得日の検出ユーティリティ等を実装。
  - src/kabusys/data/__init__.py / etl.py
    - ETLResult を公開インターフェースとして再エクスポート。
- その他
  - テスト容易性を考慮した設計（内部の API 呼び出しをモック可能にするフックを用意）。
  - DuckDB のバージョン固有挙動（executemany の空リスト制約やリスト型バインドの不安定さ）へのワークアラウンドを導入。
  - OpenAI モデルに gpt-4o-mini を使用するデフォルトを設定し、JSON Mode（response_format）対応を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の扱いにて OS 環境変数を保護する仕組みを導入（protected set）。.env ファイルを読み込む際は既存の環境変数を必要に応じて上書きしないデフォルト挙動。

Notes / マイグレーション & 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の設定が Settings で必須になっています。欠如時は ValueError を発生します。
  - OpenAI を使う機能（score_news, score_regime）は OPENAI_API_KEY が必要（関数引数でも指定可）。未設定時は ValueError。
- .env の自動読み込み:
  - パッケージは import 時にプロジェクトルートを探索して .env/.env.local を自動的に読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストや CI 環境向け）。
- ルックアヘッドバイアス防止:
  - AI / リサーチ関連関数は内部で datetime.today()/date.today() を参照せず、呼び出し側が明示的に target_date を渡す設計になっています。バッチ処理やバックテスト時に意図しない未来情報を参照しないよう注意してください。
- DuckDB 互換性:
  - executemany に空リストを渡すと問題になるバージョンに対応するため、空チェックを行っています。DuckDB バージョン差に注意して運用してください。
- テスト:
  - OpenAI 呼び出しの内部ヘルパー（各モジュールの _call_openai_api）を unittest.mock.patch で差し替え可能です。外部 API を切り離したユニットテストが容易に行えます。

今後の予定（例）
- Strategy / Execution / Monitoring の具体的実装（現行はパッケージレベルのエクスポートが存在）。
- より豊富なファクター、品質チェックルールの追加。
- OpenAI 呼び出しのレート管理やメトリクス収集の強化。
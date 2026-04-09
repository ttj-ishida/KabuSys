# Changelog

すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しており、セマンティックバージョニングを使用します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（互換性に影響する可能性あり）
- Fixed: バグ修正
- Security: セキュリティ対応

[Unreleased]

---

[0.1.0] - 2026-04-09
=================================

Added
-----
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py にてバージョン `0.1.0` を公開。パッケージの公開インターフェースとして data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / ロード機能
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export KEY=val 形式やクォート／エスケープ、インラインコメントを考慮した独自パーサを実装（_parse_env_line）。
    - override / protected オプションにより OS 環境変数の保護・上書き制御を提供。
    - Settings クラスを導入し、アプリ設定をプロパティ経由で取得:
      - J-Quants / kabu ステーション / LINE / DB パス等の設定を提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
      - 環境タイプ (development/paper_trading/live) とログレベルの検証。
      - プロパティで is_live / is_paper / is_dev を提供。

- データプラットフォーム機能（DuckDB と連携）
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨格を実装。差分取得、保存（idempotent）、品質チェックを想定。
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題の集計、to_dict() サポート）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート（公開インターフェース）。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの管理ロジックを実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar が未登録の場合は曜日ベースのフォールバック（週末除外）。
      - calendar_update_job により J-Quants API からの差分取得と冪等保存（バックフィル・健全性チェックを含む）を実装。
    - DuckDB の日付変換ユーティリティやテーブル存在チェック等の内部関数を提供。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算機能を実装（prices_daily / raw_financials を参照）:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
      - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - データ不足時に None を返す安全設計、スキャン範囲のバッファ設定を導入。
  - src/kabusys/research/feature_exploration.py
    - 研究向けの分析ユーティリティを実装:
      - calc_forward_returns: 指定ホライズン先の将来リターン（デフォルト [1,5,21]）を計算。
      - calc_ic: factor と将来リターン間の Spearman ランク相関（IC）を計算。十分なデータがなければ None を返す。
      - rank: 同順位は平均ランクとするランク付け関数（丸めによる ties 対応）。
      - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
  - src/kabusys/research/__init__.py
    - 主要関数を再エクスポートして公開。

- AI（自然言語処理）モジュール（OpenAI と連携）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄ごとのセンチメントスコアリング機能を実装。
      - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で計算。
      - news_symbols と raw_news を結合して銘柄ごとに記事を集約し、1銘柄につき最大記事数・最大文字数でトリム。
      - 最大 20 銘柄ごとに gpt-4o-mini（JSON Mode）へバッチ送信し、429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
      - レスポンスのバリデーション（JSON 抽出、results リスト、code と score の検証）と ±1.0 でのクリップ。
      - 成功した銘柄分のみ ai_scores テーブルへ冪等置換（DELETE→INSERT）を実施。
      - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。
  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定モジュールを実装（ETF 1321 の 200 日 MA 乖離とマクロニュースのセンチメントを統合）。
      - _calc_ma200_ratio により 1321 の直近 200 日の MA 乖離（最新終値 / MA200）を計算。データ不足時は中立（1.0）。
      - _fetch_macro_news でマクロ関連キーワードを含むタイトルを取得（最大 20 件）。
      - OpenAI (gpt-4o-mini) を用いてマクロセンチメントを評価し、重み付けして最終レジームスコアを合成（MA:70%, Macro:30%）。
      - レジームラベルは閾値により 'bull' / 'neutral' / 'bear' を判定。
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。API エラー等の際は macro_sentiment=0.0 でフェイルセーフ。
  - src/kabusys/ai/__init__.py
    - news_nlp.score_news を公開（score_news を外部から利用可能）。
    - news_nlp の score_news と regime_detector の score_regime はテスト差し替え用フック（内部 _call_openai_api を patch）に配慮して実装。

Changed
-------
- N/A（初期リリースのため既存機能の変更はなし）。

Fixed
-----
- N/A（初期リリース）。

Security
--------
- 環境変数取り扱いにおいて OS 環境変数を保護する設計（config._load_env_file の protected 引数）を導入。

Notes / 設計方針の重要点
-----------------------
- ルックアヘッドバイアス防止:
  - AI モジュール、研究モジュール、ETL/カレンダー関連の各関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計になっています（再現性とバックテスト安全性のため）。
- フェイルセーフ:
  - OpenAI API 呼び出しや外部 API 呼び出しで致命的な失敗が発生しても、可能な範囲でゼロ値やスキップで継続する方針（部分失敗時に他データを保護）。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、現行 DuckDB バージョンの挙動を考慮した実装を行っています。
- テストしやすさ:
  - AI 呼び出し箇所は内部 _call_openai_api をモジュールローカルに実装しており、unittest.mock.patch により容易に差し替え可能。

既知の注意点 / 今後の作業
--------------------------
- export したパッケージ __all__ に monitoring が含まれますが、monitoring モジュールの実体や詳細実装はこのリリースのソースからは確認できません（今後追加される想定）。
- ドキュメント（ユーザ向けの使い方ガイド、API キーのセットアップ例、DB スキーマ定義など）は別途整備予定。
- OpenAI モデル指定は現状 gpt-4o-mini を想定しているため、API 仕様変更時の対応が必要となる可能性があります。

---

この CHANGELOG はコードベースから推測して作成しています。必要に応じて日付・内容の修正を行ってください。
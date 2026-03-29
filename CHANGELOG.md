# Changelog

すべての重要な変更点をここに記載します。本ファイルは Keep a Changelog の形式に従っています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### 追加 (Added)
- パッケージ初期実装
  - src/kabusys/__init__.py
    - パッケージメタ情報とサブモジュール公開（data, strategy, execution, monitoring）。
    - バージョン: 0.1.0

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルと環境変数の読み込み機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD 非依存で自動ロード可能。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）、上書き保護（protected keys）をサポート。
    - 複数の .env 構文（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント）に対応したパーサを実装。
    - 環境変数自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD オプション。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などの設定プロパティを公開。入力値検証（有効値セット）を実装。

- AI（ニュースNLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメントスコアを算出する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数制限（記事数上限・1銘柄あたり文字トリム）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。失敗時はフェイルセーフでスキップし続行。
    - OpenAI レスポンスの厳密なバリデーション（JSON復元、キー検証、数値変換、既知コードフィルタ）を実装し、不正レスポンスは無害化。
    - DuckDB への書き込みは冪等操作（DELETE → INSERT）として実装。DuckDB の executemany の空リスト制約に対するワークアラウンドを実装。
    - score_news API を公開（DuckDB 接続と target_date を受けとる）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を推定する機能を実装。
    - ma200_ratio の計算、マクロキーワードでフィルタしたニュース取得、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、スコア合成と閾値判定を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。API 呼び出しの失敗や JSON パース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - lookahead バイアス防止（date.today() を直接参照しない、prices_daily は target_date 未満データのみ使用）。

- データ / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫したロジックを提供。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近日数再取得）・保存を行う。健全性チェックや例外ハンドリングを実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの主要ロジック（差分取得、保存、品質チェックの呼び出し、バックフィル戦略）を実装。
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題リスト、エラーリスト等）。
    - テーブル存在チェック、最終日取得ユーティリティ等を提供。
    - J-Quants クライアントおよび quality モジュールとの連携点を用意。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。

  - src/kabusys/data/__init__.py
    - data パッケージの基盤（空ファイルでパッケージ化）。

- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づくファクター群（Momentum / Volatility / Value / Liquidity）を計算する関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
      - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の算出
    - DuckDB を用いた SQL ベースの実装で、外部 API へのアクセスはなし。

  - src/kabusys/research/feature_exploration.py
    - 研究用ユーティリティを実装:
      - calc_forward_returns: 任意ホライズンの将来リターン計算（複数ホライズンを同時取得）
      - calc_ic: スピアマンのランク相関（IC）計算（欠損・十分なサンプル数の検証あり）
      - rank: 平均ランク（同順位は平均ランク扱い、丸めによる ties 対策あり）
      - factor_summary: カラム単位の基本統計量（count/mean/std/min/max/median）
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。

  - src/kabusys/research/__init__.py
    - 研究用 API をエクスポート（ファクター計算・統計ユーティリティの公開）。

- その他
  - src/kabusys/ai/__init__.py
    - score_news をエクスポート。

### 変更 (Changed)
- なし（初回リリースのため新規実装のみ）。

### 修正 (Fixed)
- なし

### セキュリティ (Security)
- OpenAI キー、API 呼び出し等の秘密情報は環境変数経由で扱う設計。ログに直接キーを出力しない実装が前提。

### 設計上の注意・実装上の工夫
- ルックアヘッドバイアス回避: 全ての AI / リサーチ関数は内部で datetime.today()/date.today() を直接参照せず、必ず外部から与えられる target_date を基準に処理します。
- DB 操作は可能な限り冪等（DELETE→INSERT / ON CONFLICT 相当）で行い、部分失敗時に既存データを保護する戦略を採用。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーションとリトライ（指数バックオフ）を実装。API 失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続できるように設計。
- DuckDB の互換性（executemany の空リスト不可等）に配慮した実装上のワークアラウンドを導入。
- 設定の自動ロードはプロジェクトルート検出に依存し、CI/テスト環境向けに自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

---

今後のリリースでは、strategy / execution / monitoring サブモジュールの具体的な取引ロジック、より詳細な品質チェック・モニタリング、ユニットテスト・CI 統合、ドキュメント強化などを予定しています。
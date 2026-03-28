# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/）に準拠します。

なお、本CHANGELOGはソースコードの内容から推測して作成した初期リリース記録です。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能は以下のとおりです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージの公開モジュールを定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0

- 環境設定・自動 .env ロード機能
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式やクォート／エスケープ、インラインコメント処理に対応した .env パーサ実装。
    - .env.local は .env を上書き (.env.local の優先度が高い)、既存の OS 環境変数は保護。
    - Settings クラスで主要な設定値をプロパティとして公開（J-Quants、kabuステーション、Slack、DB パス、実行環境・ログレベルの検証等）。
    - KABUSYS_ENV や LOG_LEVEL の入力検証と便利な is_live / is_paper / is_dev フラグを提供。

- ニュース NLP（センチメント）スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとのニュース集約を行い、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを取得。
    - JST基準のタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を実装（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE = 20 銘柄）、1銘柄あたりの記事数・文字数上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) によるトリム実装。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、レスポンス検証（JSON パース、構造・型・コード検証）を実装。
    - スコアは ±1.0 にクリップ。部分成功時は既存スコアを保護するため対象コードのみ DELETE→INSERT で更新。
    - テスト容易性のため OpenAI 呼び出し箇所はパッチ可能（_call_openai_api の分離）。

- 市場レジーム判定モジュール
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - calc_news_window を利用してニュースウィンドウを決定し、_fetch_macro_news でマクロキーワードにマッチする記事タイトルを抽出。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント算出と、フェイルセーフでの macro_sentiment=0.0 フォールバック。
    - スコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）し、エラー時は ROLLBACK を試行。
    - LLM 呼び出しは独立実装でモジュール間結合を避け、テスト用に差し替え可能。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar が未取得の場合は曜日ベースのフォールバック（週末は休場）を行う。
    - calendar_update_job にて J-Quants から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを実装。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL の結果を表現する ETLResult dataclass を提供（取得数、保存数、品質問題、エラー一覧など）。
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェックの流れを想定したユーティリティ関数群（内部ユーティリティを含む）。
    - _get_max_date 等の DB ヘルパーを提供。

- リサーチ（研究）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン・MA200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB SQL を用いた効率的な窓関数（OVER）実装、データ不足時の None 処理、関数は prices_daily / raw_financials のみ参照。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）、IC（スピアマン順位相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純粋標準ライブラリ + DuckDB 実装。

- 研究用ユーティリティのエクスポート
  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から）。

- その他
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 破壊的変更 (Removed / Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

設計上の注意点・保守上のポイント（実装から推測）
- LLM 呼び出しはリトライ・バックオフ・タイムアウト・5xx 判定を行い、API 失敗時は安全側のデフォルト（例: macro_sentiment=0.0）で継続することでフェイルセーフ性を確保。
- レジーム判定・ニューススコア算出等はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を注入する設計。
- DB 書き込みは冪等性を重視（DELETE→INSERT のパターンや ON CONFLICT を想定）、コミット/ロールバック処理を組み込んでいる。
- テスト容易性のため外部 API 呼び出しポイント（_call_openai_api 等）は差し替え可能に分離している。
- .env 自動読み込みは便利だが、KABUSYS_DISABLE_AUTO_ENV_LOAD フラグでテスト環境からの影響を抑制できる。

このCHANGELOGはコードベースの実装から推測した内容に基づき作成しています。実際のリリースノートとして使用する場合は、追加の変更点や運用上の注意（例: 必須環境変数一覧、マイグレーション手順など）を追記してください。
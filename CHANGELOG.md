# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28
初回リリース — 基本的なデータパイプライン、リサーチ/ファクター分析、AI ベースのニュース/NLP 評価、および運用ユーティリティを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ にて定義）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートの検出 .git または pyproject.toml を使用）。
  - .env パーサーの実装: export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数。
  - 保護された OS 環境変数の扱い（上書き制御）。
  - Settings クラスによる型付きプロパティ提供: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなど。
  - 必須環境変数未設定時の明示的なエラー (_require)。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（calc_news_window）。
    - raw_news + news_symbols を銘柄ごとに集約し、最大記事数・文字数でトリムして OpenAI（gpt-4o-mini）へバッチ評価。
    - バッチサイズ・リトライ・指数バックオフ・レスポンスバリデーション（JSON モードの復元処理を含む）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト用の API 呼び出し差し替えポイント（_call_openai_api の patch を想定）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）評価。
    - マクロ記事抽出（キーワードベース）、LLM 呼び出し（gpt-4o-mini）、再試行ロジック、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 共通設計方針: ルックアヘッドバイアス回避（datetime.today()/date.today() を使用しない）、API フェイルセーフ、テスト用差し替え点。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar に基づく営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバック。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・冪等保存。
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した ETL の設計骨格。
    - DuckDB に対する存在チェックや最大日付取得などのユーティリティ実装。
  - jquants_client との連携ポイントを想定（fetch/save 関数の呼び出し場所を確保）。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials の直近財務データと株価から PER / ROE を算出。
    - DuckDB ベースの SQL 実装と結果を dict のリストで返すインターフェース。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン先のリターンを一括取得。
    - Information Coefficient 計算 (calc_ic): スピアマンのランク相関を実装（rank ユーティリティを含む）。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を算出。

### 変更 (Changed)
- 初回リリースのため該当なし（新規実装）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数のロードにおいて OS 環境変数を保護する仕組みを導入（.env の上書き制御）。
- OpenAI API キーは明示的な引数または環境変数（OPENAI_API_KEY）で注入。未設定時は ValueError を送出して誤動作を防止。

### 注意事項 / 移行メモ (Notes)
- 動作前提
  - DuckDB を利用する設計（DuckDBPyConnection 型を多数引数で受ける）。DuckDB のバージョン差異（executemany の空リスト扱いなど）への注意喚起がコード内にあるため運用時は互換性確認を推奨。
  - OpenAI（gpt-4o-mini）利用部分は API キー必須。API 利用料・レート制限に注意。
- テスト向けフック
  - OpenAI 呼び出しは内部で _call_openai_api を使用しており、unittest.mock.patch による差し替えが容易に行えるよう設計されています。
- ルックアヘッドバイアス対策
  - 主要な処理（ニュースウィンドウ計算、レジーム判定、スコア生成等）は datetime.today()/date.today() に依存しないため、正しい日付を引数で与えれば再現可能な処理となっています。
- 環境変数名（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY

今後の予定（例）
- ETL の具象実装（jquants_client の完全統合）、品質チェックルールの拡充、モニタリング/実行周りの実装強化などを想定しています。
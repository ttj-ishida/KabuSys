CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
安定版リリースはセマンティックバージョニングに従います。

[0.1.0] - 2026-04-02
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買・データ基盤向けコアモジュール群を追加。
  - パッケージ構成:
    - kabusys (パッケージルート)
      - data: データ取得・ETL・カレンダー管理等
      - ai: ニュースNLP / 市場レジーム判定
      - research: ファクター計算・特徴量解析ユーティリティ
      - config: 環境変数/設定管理
  - 公開 API / 再エクスポート:
    - kabusys.__init__.py により主要サブパッケージを公開（data, strategy, execution, monitoring を __all__ に設定）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 環境設定（kabusys.config.Settings）
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
  - OS 環境変数を protected として上書きを防ぐ挙動。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須/任意設定プロパティ群を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - ファイル・パス系のデフォルト値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）と監視閾値（CPU/MEM/DISK）を設定。
  - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の検証を実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
  - バッチ/チャンク単位処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数上限（記事数:10, 文字数:3000）によるトリム。
  - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。非リトライのエラーはスキップして継続。
  - レスポンスの堅牢なバリデーション実装（JSON復元/キー検査/数値検査/未知コード無視）。
  - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込み。
  - calc_news_window: JST基準のニュース収集ウィンドウ計算ユーティリティを提供。
  - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モジュール内で _call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を算出。
  - LLM によるマクロセンチメントはニュースタイトルのフィルタリング（マクロキーワード群）＋ gpt-4o-mini JSON mode で評価。
  - 再試行（リトライ）/エクスポネンシャルバックオフ / フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
  - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアス対策: date 比較は target_date 未満・datetime.today() を参照しない設計。

- データ基盤
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・保存（バックフィル・健全性チェックあり）。
    - 営業日判定と関連ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB登録値優先、未登録日は曜日ベースでフォールバック。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
  - pipeline / etl:
    - ETLResult データクラス（取得件数・保存件数・品質チェック問題・エラー集約）を実装。
    - 差分更新・バックフィル・品質チェック方針に基づく骨組みを実装（jquants_client / quality モジュールを使用）。
    - DuckDB に対する互換性考慮（executemany の空リスト不可等）を反映した実装。

- リサーチ・ファクター（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等のファクター計算関数を SQL ベースで実装（DuckDB）。
    - データ不足時は None を返す設計。戻り値は (date, code) を含む dict のリスト。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman ランク相関）、rank、factor_summary（統計サマリー）を実装。
    - pandas 等外部依存なしで純標準ライブラリ＋DuckDB で実装。
    - 入力検証（horizons の範囲等）を実装。

- ロギング・ドキュメント化
  - 各モジュールで処理状況と異常時のログ出力を充実させ、外部 API エラーや DB トランザクション失敗時のハンドリングを明確化。

Security
- 環境変数取り扱い上の注意点を明記（必須トークンは Settings 経由で取得し、未設定時は ValueError を送出）。
- .env 自動読み込み時に OS 環境変数を保護する設計（protected set）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- DuckDB バージョン互換性:
  - executemany に空リストを与えると例外になるバージョン（例: DuckDB 0.10）があるため、コード中で空リストのチェックをしている。
- OpenAI API:
  - gpt-4o-mini を JSON mode（response_format={"type":"json_object"}）で使用する想定。API の変化やモデル差異によりパースやエラー処理の追加対応が必要となる可能性がある。
  - OPENAI_API_KEY が未設定の場合、一部関数は ValueError を投げる（score_news, score_regime）。
- ルックアヘッド対策:
  - 全 AI / ETL / リサーチ関数で datetime.today() / date.today() を直接参照しない設計が採られている（テスト時や再現性のため target_date を明示的に渡す）。
- フェイルセーフ:
  - LLM/API エラー発生時は多数の箇所で 0.0 戻し値やスキップを行い、上位システムの可用性を優先する方針。

Migration / Usage Notes
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings のプロパティ参照を参照）。
  - OPENAI_API_KEY は AI 関連処理（score_news / score_regime）で必須。
- .env の自動ロードはプロジェクトルートが .git または pyproject.toml を検出できる場合に有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Contributors
- 初回コードベースの実装により構成された機能群（モジュール内の docstring に設計方針・仕様を記載）。

この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴・変更履歴が別途存在する場合は、それに合わせて更新してください。
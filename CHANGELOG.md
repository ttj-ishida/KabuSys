CHANGELOG
=========

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。　　

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリース。日本株自動売買システムの基本コンポーネントを提供。
  - パッケージの公開 API:
    - pakage: kabusys
    - __all__: ["data", "strategy", "execution", "monitoring"]
    - パッケージバージョン: 0.1.0
- 環境変数・設定管理 (kabusys.config)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートの有無に応じた判定）。
  - 読み込み時の上書き制御: override と protected（OS 環境変数を保護）をサポート。
  - Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須/任意設定をプロパティとして公開（デフォルト値やパスは Path として提供）。
    - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH 等。
    - 監視閾値（CPU/MEM/DISK）、KILL フラグの振る舞い、ログレベルと環境（development/paper_trading/live）の検証ロジックを実装。
    - 設定未存在時は _require が ValueError を送出して明示的に失敗させる。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から記事を集約し銘柄毎に OpenAI （gpt-4o-mini）へバッチ送信して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換して DB 比較）。
    - バッチサイズ、記事数上限、文字数トリム、結果の JSON バリデーション、スコアの ±1.0 クリップを実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフと最大リトライ制御。
    - レスポンス検証で安全にスキップする設計（部分失敗時でも他銘柄のデータを保護するため、DELETE→INSERT のコード絞込み書き込み）。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - メイン処理: ma200_ratio 計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼び出し専用の内部関数を持ち、news_nlp と結合しない設計（モジュール間の疎結合）。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルの有無に応じた営業日判定ロジック（DB 値優先、未登録は曜日ベースのフォールバック）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル（日次の訂正取り込み）、健全性チェックを実装。
    - 最大探索範囲やバックフィル期間、先読み日数、健全性閾値を定義。
  - ETL パイプライン (pipeline)
    - 差分更新、保存（jquants_client の save_* を想定した冪等保存）、品質チェックの統合フロー設計。
    - ETLResult データクラスの導入（結果の要約、品質問題・エラーリスト、to_dict メソッド）。
    - デフォルトのバックフィル日数と最小データ日付を定義。
  - etl.py に ETLResult を再エクスポート。
  - jquants_client（参照）を利用する設計（実装は外部モジュール想定）。
- リサーチ／特徴量 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、平均売買代金、出来高比率、PER/ROE の計算関数を実装。
    - DuckDB に対する SQL ベースの実装。データ不足時は None を返すなど堅牢化。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
- その他
  - すべての DB 書き込みにおいて冪等性とトランザクションを重視（BEGIN / DELETE / INSERT / COMMIT と例外時の ROLLBACK を実装）。
  - ロギングと警告ログの充実: データ不足や API エラー、ROLLBACK 失敗などを明示的にログ出力。

Security
- 環境変数読み込み時に OS 環境変数を protected として上書きしないデフォルト挙動を採用。CI/本番の上書きを防止。
- 必須情報（例: OpenAI API キー、J-Quants トークン、kabu API パスワード）は明確に検証し、未設定時には ValueError を発生させる。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Broken / Deprecated
- なし（初回リリース）。

Notes / 運用上の注意
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings の該当プロパティ参照）。
  - OpenAI の利用: OPENAI_API_KEY を環境変数で渡すか、score_news / score_regime の api_key 引数を指定する。
- デフォルトファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - PID / Kill フラグ等もデフォルトパスあり（Settings を参照）。
- OpenAI:
  - gpt-4o-mini を想定したプロンプトと JSON Mode を使用。レスポンス形式の変動に備え堅牢なパースとフォールバックを実装しているが、OpenAI SDK/モデルの大幅な仕様変更が発生した場合は追加対応が必要。
- DuckDB:
  - 一部の executemany/配列バインドに関する注釈や互換性配慮（DuckDB 0.10 系への互換性確保）がソース内に記載されているため、DuckDB バージョンアップ時は注意が必要。
- ルックアヘッドバイアス対策:
  - すべての分析・スコアリング関数は datetime.today() / date.today() を直接参照しない設計。target_date に依存して過去データのみを参照する実装になっている。
- テスト支援:
  - OpenAI 呼び出し箇所は内部の _call_openai_api を patch することでモック化可能。

依存関係（実行時の想定）
- duckdb
- openai（OpenAI Python SDK）
- 外部 API クライアント: J-Quants 用モジュール（kabusys.data.jquants_client を想定）
- 標準ライブラリ（pathlib, os, logging, json, datetime など）

将来の改善候補（既知の制約）
- value ファクター: PBR / 配当利回りは未実装（TODO として言及）。
- ニュース NLP のモデルやプロンプト最適化、レスポンス検証ルールの強化（より多言語や細粒度の評価対応）。
- calendar_update_job の API 呼び出しや保存の失敗時のリカバリや再試行方針の拡張。

貢献・報告
- バグや改善提案は Issue を作成してください。コード中にテストフックや明示的な例外ログを備えていますので、再現手順の添付をお願いします。
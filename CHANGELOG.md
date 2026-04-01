Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この変更履歴はリポジトリ内のソースコードを元に推測して作成しています。実際のコミット履歴とは異なる可能性があります。

フォーマット:
- 変更はカテゴリー別に分けています（Added, Changed, Fixed, Security）。
- 日付は本ファイル作成日（2026-04-01）を使用しています。

Changelog
=========

すべての注目すべき変更はここに記載します。  
フォーマットの詳細は Keep a Changelog を参照してください。

[Unreleased]
------------

- 開発中のワークやマイナー修正をここに記載します（現時点では未リリース）。

[0.1.0] - 2026-04-01
--------------------

Added
- 基本パッケージ初期リリース
  - パッケージ名: kabusys、バージョン 0.1.0 を package-level に定義（src/kabusys/__init__.py）。
  - public モジュール群を __all__ で公開: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export KEY=val 形式やクォート／エスケープ、インラインコメント等を考慮した .env パーサを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム関連の設定をプロパティ経由で取得。必須設定は _require() で ValueError を投げる。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーション実装。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを取得する処理を実装。
    - バッチ処理（最大 20 銘柄／リクエスト）、トークン肥大化対策（記事数上限、文字数トリム）を実装。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリッピング。
    - ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込む実装。部分失敗時に既存スコアを保護する設計。
    - calc_news_window() を公開し、JST（前日15:00～当日08:30）→ UTC 変換ロジックを提供。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime() を実装。
    - prices_daily / raw_news を参照して ma200_ratio を計算、news_nlp と同様に OpenAI を呼んで macro_sentiment を取得（記事がなければ呼ばない）。
    - OpenAI 呼び出しは独立した実装で、フェイルセーフとして API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）をサポート。

- データプラットフォーム関連 (src/kabusys/data/)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを使った営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（週末は休業）でフォールバックする一貫した振る舞い。
    - calendar_update_job() により J-Quants API から差分取得して冪等的に保存する処理を実装（バックフィル、健全性チェック含む）。

  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを導入し、ETL 実行結果、取得数・保存数・品質チェック結果・エラー概要を集約できるようにした。
    - 差分更新、バックフィル、品質チェックのフローを想定した設計（jquants_client と quality モジュールと連携する想定）。
    - pipeline の ETLResult を data.etl から再エクスポート。

- リサーチツール群 (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL ウィンドウ関数を活用して営業日ベースのホライズン計算を実装。
    - データ不足時には None を返す堅牢な設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存なしで標準ライブラリと DuckDB のみで動作する設計。

Changed
- 設計方針・実装ガイドラインを明文化
  - 全体を通じて「ルックアヘッドバイアスを防ぐ」ために datetime.today()/date.today() を直接参照しない設計方針が適用されている点を明示。
  - OpenAI 呼び出しはテスト容易性のため差し替え可能（ユニットテストで _call_openai_api をパッチする想定）。

Fixed
- n/a（この初期リリースは新規実装を中心にまとめられています。実運用で報告された不具合は次バージョンで修正予定）

Security
- 環境変数取り扱いに関する注意点を実装
  - 必須キー未設定時は明示的に ValueError をスローして早期検出。
  - .env の読み込みで OS 環境変数を保護する protected キーセットを導入し、.env.local による上書きを制御可能。

Notes / 注意事項
- OpenAI（gpt-4o-mini）を利用する機能は API キーの注入（api_key 引数または環境変数 OPENAI_API_KEY）を必須とする。未設定時は ValueError を送出。
- DuckDB のバージョンや executemany の挙動依存（空リストバインド不可）を考慮した実装になっているため、DuckDB の互換性に注意。
- jquants_client / quality / monitoring / execution 等の外部インターフェースはモジュール参照として組み込まれているが、実際の API クライアント実装や DB スキーマはリポジトリ外（または別ファイル）に依存する。

参照
- この CHANGELOG はソースファイル群（src/kabusys 以下）を基に作成しています。各関数や振る舞いの詳細は該当ソースファイルの docstring と実装を参照してください。

--- 
今後の推奨
- 実稼働前に OpenAI 呼び出し・DuckDB 書き込みの統合テストを実施してください。
- .env.example をリポジトリに含め、必要な環境変数を明確にすることを推奨します。
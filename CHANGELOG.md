CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日を示します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。
- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - OS 環境変数を保護する protected 機能（.env.local は既存キーを上書き可能）。
  - Settings クラスでアプリケーション設定を公開（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DB パス、環境/env ロジック、ログレベル等）。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにテキストを作成し、OpenAI（gpt-4o-mini）の JSON モードでバッチ解析して ai_scores テーブルへ保存。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、最大記事数/文字数トリム、チャンク処理（最大 20 銘柄/コール）、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。API 呼び出しはテスト用にパッチ可能（内部 _call_openai_api をモック）。
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして他銘柄処理を継続。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタして記事タイトルを抽出、OpenAI で JSON 出力（{"macro_sentiment":..}）を期待。API 呼び出しは別実装でモジュール結合を避ける。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライロジック、最大記事数制限、ルックアヘッドバイアス回避（datetime.today() を参照しない設計）。
- データモジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定・次/前営業日検索・期間内営業日取得・SQ 日判定などのユーティリティ実装。
    - DB 登録値優先、未登録日は曜日（土日）ベースのフォールバック。探索の最大範囲制限やバックフィル・健全性チェックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存する夜間バッチロジック（バックフィル・健全性チェック付き）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - 差分取得・保存（jquants_client 経由で idempotent 保存）・品質チェック統合のための ETLResult 型とユーティリティ実装。
    - ETLResult は品質問題やエラー情報を集約して呼び出し元が判断できるように設計。
- 研究（research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR、相対 ATR、出来高/売買代金指標）、Value（PER、ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、結果を (date, code) キーの dict リストで返却。
    - DuckDB のウィンドウ関数を利用し、ルックアヘッドバイアスを避ける設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証付き）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関、最小サンプル数チェック）。
    - ランク関数（rank: 同順位は平均ランク）、統計サマリー（factor_summary: count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリのみで実装。
- テスト/運用を意識した設計
  - OpenAI API 呼び出し箇所は内部関数をモック可能にしてユニットテストを容易化。
  - DB 書き込みは冪等性（DELETE→INSERT / BEGIN/COMMIT/ROLLBACK）を確保し、失敗時に ROLLBACK を試みるログ処理を実装。
- その他
  - ETL, カレンダー, 研究用関数はいずれも DuckDB 接続を引数に取り、本番の発注 API 等へアクセスしない安全設計。
  - デフォルト DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を Settings で提供。
  - 必須環境変数を明示（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、OPENAI_API_KEY 使用を想定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Requirements
- 外部依存: openai SDK（OpenAI クライアント）、duckdb。  
- OpenAI API は JSON Mode（response_format={"type": "json_object"}）を使用する想定。  
- 設定方法: .env/.env.local または環境変数。README/ドキュメントで .env.example を参照する想定。  

今後の予定（例）
- ai モデルやプロンプトの微調整、より詳細なログ/メトリクスの追加。  
- ETL の部分的再実行・監査ログの強化、品質チェックの運用改善。  
- research モジュールでの追加ファクター／可視化ツールの追加。

--- 
この CHANGELOG はコードベース（src/ 配下）の実装内容から推測して作成しています。実際のリリースノートとして公開する前に、必要に応じて文言や日付・範囲を調整してください。
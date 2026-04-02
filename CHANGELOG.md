CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

0.1.0 - 2026-04-02
------------------

Added
- 初期リリース: パッケージ kabusys (バージョン 0.1.0) を公開。
  - パッケージ公開点: src/kabusys/__init__.py による主要サブパッケージのエクスポート（data, research, ai などを含むモジュール群を想定）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env ファイルのパースは以下の点に対応:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行頭コメント・インラインコメントの適切な扱い
  - OS 環境変数は protected として上書き保護（override パラメータ使用時も保護）。
  - 必須環境変数取得ヘルパー _require と、Settings クラスを提供。Settings は以下の設定をプロパティで取得:
    - J-Quants / kabuステーション / Slack / データベース（DuckDB / SQLite）パス
    - 監視用設定（PID ファイルパス、CPU/Memory/Disk のしきい値）
    - 環境種別（development / paper_trading / live）の検証
    - ログレベル検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 環境設定のバリデーションとフェイルファスト設計。

- AI モジュール（src/kabusys/ai/news_nlp.py, src/kabusys/ai/regime_detector.py）
  - ニュースセンチメント解析（news_nlp.score_news）:
    - raw_news と news_symbols を集約して銘柄ごとにテキストを作成し、OpenAI（デフォルト gpt-4o-mini）にバッチで送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク化（最大_Batch サイズ）・1銘柄あたり記事数・文字数上限などトークン肥大化対策を実装。
    - JSON Mode のレスポンスを厳密にバリデーションし、未知コードは無視、スコアは ±1.0 にクリップ。
    - API エラー（429, ネットワーク断, タイムアウト, 5xx）は指数バックオフでリトライ。その他のエラーはスキップして継続する設計（フェイルセーフ）。
    - スコア結果は ai_scores テーブルへ（冪等的に）DELETE → INSERT の置換で保存し、部分失敗時にも既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能にしている。
    - calc_news_window により JST の特定時間ウィンドウを UTC naive datetime に変換するユーティリティを提供。
  - 市場レジーム判定（regime_detector.score_regime）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - DuckDB の prices_daily / raw_news を参照して ma200_ratio を算出（ルックアヘッド防止のため target_date 未満のみ使用）。
    - マクロニュースはキーワードフィルタで抽出し、OpenAI により macro_sentiment を算出。API 失敗時は 0.0 にフォールバック。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しはニュースモジュールと独立した実装とし、モジュール結合を避ける設計。

- データプラットフォーム / ETL（src/kabusys/data/）
  - ETL パイプラインのインターフェース ETLResult（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py を経由して公開）:
    - ETL 実行結果を表すデータクラス（取得件数、保存件数、品質問題、エラーリスト等）、辞書化ユーティリティを提供。
    - 品質チェック（quality モジュール想定）との連携用フィールドを用意。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar テーブルと連携する営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースでフォールバックする堅牢なロジック。
    - calendar_update_job で J-Quants API から差分取得 → 冪等保存を行うバッチ処理を実装。バックフィル・健全性チェック（将来日付異常）を実装。
    - jquants_client 経由での取得および保存インターフェースを想定（jq.fetch_market_calendar / jq.save_market_calendar）。
  - 汎用的な内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。

- 研究 / ファクター（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等の計算ロジックを実装。
    - DuckDB の SQL + Python を併用し、prices_daily / raw_financials のみを参照する安全な実装。
    - 結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで記述。
  - research パッケージは data.stats.zscore_normalize を再エクスポート。

- ロギング・設計上の配慮
  - 各モジュールで詳細な logging 設定を行い、失敗時に警告・例外ログを残す設計。
  - ルックアヘッドバイアスを避けるため、datetime.today()/date.today() を直接参照しない方針（target_date を引数で渡す設計を採用）。
  - DuckDB を主要なローカル分析データベースとして想定（DuckDB 接続を受ける関数インターフェース）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes (既知の制限・注意事項)
- OpenAI API の利用は環境変数 OPENAI_API_KEY または関数引数でキーを提供する必要がある（未設定時は ValueError を送出）。
- JSON Mode を利用する想定だが、LLM の出力が必ずしも厳密 JSON ではないケースに備え、応答パースの復元処理を実装している（それでもパース失敗時はスキップし 0.0 等にフォールバック）。
- ai/news_nlp と ai/regime_detector はそれぞれ内部で _call_openai_api を独立実装しており、モジュール間でプライベート関数を共有しない設計。テスト時は各モジュールの _call_openai_api をモック可能。
- DuckDB バインドの挙動（executemany に空リストを渡せない等）を考慮した実装が行われているため、DuckDB のバージョン差分に注意。
- 現時点での RPC/API クライアント（jquants_client 等）、quality モジュール、strategy / execution / monitoring の具体実装は含まれていない（インターフェースを想定）。

今後の予定（例）
- strategy / execution / monitoring の実装強化（注文発注・監視ロジック）
- 品質チェック（quality）と監査ログの統合
- パッケージテストの拡充（CI、モックを用いたユニットテスト）
- OpenAI 呼び出しのより柔軟な設定（モデル切替・タイムアウト調整など）

メモ
- この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートはプロジェクト方針に応じて調整してください。
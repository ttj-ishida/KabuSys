CHANGELOG
=========

すべての重要なリリース変更をここに記録します。
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。
- 日付は YYYY-MM-DD 形式で記載します。

Unreleased
----------
（無し）

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージのトップメタ情報: src/kabusys/__init__.py に __version__="0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定・自動 .env 読み込み:
  - src/kabusys/config.py を追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export 形式、クォート、エスケープ、行内コメントを適切に処理。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB /監視/ログ等の設定プロパティを公開。
  - 必須環境変数未設定時は ValueError を発生させるヘルパーを提供（_require）。
  - 有効な環境 (development/paper_trading/live) およびログレベルのバリデーションを実装。

- AI モジュール（LLM ベースのニュース解析・市場レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用い、銘柄単位でニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を計算・ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチサイズ、文字数・記事数上限、レスポンスのバリデーション、スコアのクリップ（±1.0）、エクスポネンシャルバックオフリトライ等を実装。
    - OpenAI 呼び出し箇所はテスト用に差し替え可能（_call_openai_api を patch 可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF（1321）の 200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し日次で市場レジーム（bull/neutral/bear）を算出。
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini, JSON Mode）を実装、API失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - DuckDB を用いた冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス回避（外部で date を注入する設計）とテストフレンドリーな設計方針。

- Data モジュール（ETL・カレンダー・品質管理など）:
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー概要等を保持）。
    - 差分取得・バックフィル・品質チェック（quality モジュールと連携）方針を実装。DuckDB 接続を前提。
    - ETL の互換性・堅牢性を考慮したユーティリティ関数（テーブル存在確認・最大日付取得等）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル）の読み書き・夜間更新ジョブ calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - DB 登録がない日には曜日ベースのフォールバック処理を行い、一貫性を保つ設計。最大探索日数の制限や健全性チェック（未来日判定）あり。
    - J-Quants クライアントとの連携（差分取得・保存）用の jq.fetch_market_calendar / jq.save_market_calendar 呼び出しを実装。

- Research モジュール（ファクター・特徴量探索）:
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M）、200日MA乖離、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高比）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算で、データ不足時の None 返却・ログ出力など堅牢性を確保。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、スピアマンランク相関による IC 計算 calc_ic、ランク変換ユーティリティ rank、ファクターの統計サマリー factor_summary を実装。
    - pandas 等に依存しない純標準ライブラリ実装で、欠損・有限値チェック等を行う。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から取得）。

- テスト・開発支援:
  - OpenAI 呼び出し部分を patch して差し替えやすく設計（news_nlp._call_openai_api / regime_detector._call_openai_api など）。
  - DuckDB における executemany の空リスト問題への対策（空パラメータ時は実行をスキップ）を実装。

Security
- 環境変数管理:
  - Settings は機密情報（APIキー等）を環境変数から取得。必須の API キー未設定時に明示的な例外を投げることで安全側の設計。
  - .env 読み込み時に既存の OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Implementation details
- OpenAI 関連:
  - 使用モデル: gpt-4o-mini（JSON モードを想定）。
  - レスポンスは厳密な JSON を期待するが、パース失敗時の緩和ロジック（{} の抽出等）を実装。
  - RateLimit/接続断/タイムアウト/5xx に対する指数バックオフでのリトライ実装。
  - API エラーは場合によってフェイルセーフでスコア 0.0 を採用し処理継続。

- DuckDB / DB 操作:
  - 多くの書き込みは冪等（DELETE→INSERT や ON CONFLICT 相当の保存）を想定。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）を利用し、失敗時は ROLLBACK を試みる。
  - DuckDB のバージョン互換性（executemany の空リスト問題、list 型バインドの差異等）に配慮した実装。

- ルックアヘッドバイアス対策:
  - 日次処理は target_date を明示的に受け取り、datetime.today()/date.today() を内部で参照しない設計（テスト・バックテストの健全性向上）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Acknowledgements / Developer hints
- テスト時は環境依存の自動 .env 読み込みを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
- OpenAI 呼び出しはモジュール内の private ヘルパーを patch してスタブ化できる（ユニットテスト向け）。
- ETL / AI / Research の各処理はすべて DuckDB 接続を注入することで I/O を切り離したユニットテストが可能。

--- 
（以降のリリースでは、各モジュールの API 変更・新機能・バグフィックスを上記スタイルで追記してください。）
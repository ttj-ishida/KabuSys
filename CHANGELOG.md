CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージの __version__（0.1.0）に基づきます。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys - 日本株自動売買システムの基本機能を実装。
- パッケージ初期化:
  - src/kabusys/__init__.py により data, strategy, execution, monitoring モジュールを公開。
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 環境設定管理:
  - src/kabusys/config.py を追加。
  - .env ファイルおよび環境変数から設定値を自動ロード（優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定（クォートなし時は直前が空白/タブの '#' をコメントと判定）などに対応。
  - _load_env_file の override / protected パラメータにより OS 環境変数保護が可能。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定取得メソッドおよび
    - パス設定（duckdb/sqlite/pid ファイル）
    - 監視閾値（CPU/MEM/DISK）
    - 環境（KABUSYS_ENV の検証: development / paper_trading / live）
    - ログレベル検証（LOG_LEVEL の検証）
    メソッドを用意。

- AI モジュール:
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する score_news を実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、記事トリム（最大記事数・最大文字数）、JSON Mode レスポンスの厳密検証とレスポンス復元策（前後の余計なテキストが混入した場合の {} 抽出）を実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフを実装。失敗時はスキップして処理継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し部分（_call_openai_api）をモック可能に設計。
    - DuckDB 0.10 の executemany 空リスト制約を考慮した挿入ロジック（DELETE → INSERT, executemany を空で呼ばないガード）を実装。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
    - prices_daily / raw_news を参照し、LLM（gpt-4o-mini）呼び出しは独自実装によりモジュール結合を防止。
    - API 呼び出し失敗時のフォールバック（macro_sentiment=0.0）、リトライ・バックオフ、JSON パース失敗時の安全処理を実装。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。トランザクション失敗時の ROLLBACK を考慮。

- Data モジュール:
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの基本構造を実装。差分更新、保存（jquants_client の save_* を想定）、品質チェック（quality モジュールとの連携）を設計。
    - ETLResult dataclass を追加し、実行結果集約（取得数、保存数、品質問題リスト、エラーリスト）を提供。has_errors / has_quality_errors / to_dict を実装。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティ実装（ETL 内部用）。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理モジュールを実装（market_calendar テーブルの夜間更新ジョブ calendar_update_job と営業日判定ユーティリティ群を提供）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。DB 登録値優先・未登録日は曜日ベースでフォールバック。
    - calendar_update_job は J-Quants から差分取得して安全に保存（fetch / save を jquants_client に委譲）、バックフィル、健全性チェックを実装。

- Research モジュール:
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER / ROE）および流動性指標を計算する calc_momentum / calc_volatility / calc_value を実装。全て DuckDB 上の prices_daily / raw_financials を参照する実装。
    - 計算は SQL ウィンドウ関数等を用い、データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで動作する設計。

- パブリック API/エクスポート:
  - ai パッケージの __init__ で score_news を公開。
  - research パッケージの __init__ で主要関数と zscore_normalize を公開。

Reliability / Safety
- 各種 API 呼び出し（OpenAI, J-Quants）に対してリトライ・バックオフ・フェイルセーフを組み込み、サービス停止を回避する設計。
- DB 書き込みは冪等操作（DELETE→INSERT や ON CONFLICT）やトランザクション（BEGIN/COMMIT/ROLLBACK）で安全性を確保。
- datetime.today()/date.today() に依存しない設計方針を採用（ルックアヘッドバイアスの排除）。target_date を明示して実行可能。

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode（response_format）を前提に設計しているため、将来の SDK/モデル変更時にパラメータ調整が必要となる可能性があります。
- DuckDB のバージョン差異（特に executemany とリストバインドの挙動）に注意。現実装は DuckDB 0.10 の制約を考慮したワークアラウンドを含みます。
- 一部の機能（jquants_client, quality モジュール、strategy/execution/monitoring の実装詳細）はこのリリースでのスケルトンまたは外部依存を想定しています（実稼働前に接続・権限設定が必要）。

Deprecated
- なし

Removed
- なし

Security
- 必須の機密情報（OpenAI API キー、J-Quants リフレッシュトークン、Kabu API パスワード、Slack トークン等）は Settings 経由で必須チェックを実施し、不足時は例外を投げて早期に検出する。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected 引数）。

References
- 実装は各モジュール内の docstring（Design notes / 処理フロー）に従って設計されています。テスト時には _call_openai_api の差し替え等、モック可能なポイントが用意されています。

今後の予定（例）
- strategy / execution / monitoring の具体的な発注・実行ロジックの実装と統合テスト。
- jquants_client / quality モジュールの実装・接続確認。
- CI 上での DuckDB バージョン互換性テスト、OpenAI 呼び出しのエンドツーエンド検証。
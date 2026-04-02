CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- 現在の開発中の変更はここに記載します。

[0.1.0] - 2026-04-02
--------------------

Added
- 初回公開リリース。
- パッケージ情報:
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py にて定義)
  - パブリックモジュール: data, strategy, execution, monitoring を __all__ で公開
- 設定/環境変数管理 (src/kabusys/config.py):
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサは export プレフィックス、クォート、バックスラッシュエスケープ、行内コメントなどを考慮した堅牢実装。
  - Settings クラスを提供（settings インスタンスをエクスポート）。主なプロパティ:
    - jquants_refresh_token (必須)
    - kabu_api_password (必須), kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (必須), slack_channel_id (必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb), sqlite_path (デフォルト: data/monitoring.db)
    - pid_file_path, cpu/memory/disk の閾値
    - 環境種別 KABUSYS_ENV（development/paper_trading/live）とログレベル検証
    - is_live / is_paper / is_dev のショートハンド
- AI 関連 (src/kabusys/ai):
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄毎のニュースを OpenAI（gpt-4o-mini）でバッチ評価。
    - チャンク処理（最大 20 銘柄 / チャンク）、1銘柄あたりの記事数と文字数制限を実装。
    - JSON Mode を利用しレスポンスを厳密に検証。部分失敗を考慮した idempotent な DB 書き換え（DELETE → INSERT）。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ）、失敗時はフェイルセーフでスキップ。
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを UTC naive datetime で返す。
    - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。
    - テスト補助: _call_openai_api をパッチ可能（unittest.mock.patch で差し替え可能）。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム判定（bull/neutral/bear）を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース取得はキーワードフィルタリング、LLM 呼び出しは安全なリトライとフォールバック（失敗時 macro_sentiment=0.0）。
    - score_regime(conn, target_date, api_key=None) を公開。market_regime テーブルへ冪等的に書き込み。
    - テスト補助: _call_openai_api をパッチ可能。
- データプラットフォーム (src/kabusys/data):
  - calendar_management モジュール
    - JPX カレンダーを扱うユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar がない場合は曜日ベースでフォールバック（週末: 休場）。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック含む）。
    - 最大探索幅やバックフィル期間などの安全措置を実装。
  - pipeline モジュール / ETLResult (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（etl.ETLResult）。ETL の取得数/保存数、品質問題、エラー一覧を保持。
    - ETL 処理方針: 差分更新、Idempotent 保存（jquants_client 経由）、品質チェックの収集（Fail-Fast ではない）。
    - DuckDB の制約（executemany に空リストを与えない）を考慮した実装。
- 研究用モジュール (src/kabusys/research):
  - factor_research.py:
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、流動性（20日平均売買代金／出来高比）などファクター計算関数を実装：
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの計算。返り値は (date, code) を含む dict のリスト。
  - feature_exploration.py:
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
    - IC（Spearman ランク相関）を計算する calc_ic(...)
    - ランク変換ユーティリティ rank(...)
    - ファクター統計サマリー factor_summary(...)
  - research パッケージ __init__ で主要関数を再エクスポート。
- その他ユーティリティ:
  - データ系モジュールは duckdb を主要なローカル DB として利用するよう設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注意事項（マイグレーション / 利用時メモ）
- OpenAI API:
  - API キーは関数引数（api_key）で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。
  - LLM の失敗はフェイルセーフ（スコア 0.0 またはスキップ）で扱われ、例外は上位に波及しない設計の箇所があるため、運用時はログを監視してください。
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（Settings が未設定時に ValueError を投げます）。
- DuckDB の互換性:
  - 一部処理では DuckDB の executemany に空リストを渡すと失敗するため、空チェックを行っています。
- テスト支援:
  - AI 呼び出し部分は内部の _call_openai_api をパッチすることで外部依存をモック可能です。

今後の予定（例示）
- strategy / execution / monitoring の具体実装と公開 API の整備
- ETL の品質チェックルール拡張とアラート連携（Slack 等）
- モデル評価・バックテスト用ユーティリティの追加

References
- 各モジュールの詳細はソースコメント（docstring）を参照してください。
保持すべき変更履歴フォーマットに従い、コードベースから推測した初回リリース向けの CHANGELOG.md（日本語）を作成しました。

CHANGELOG.md
=============

すべての目立つ変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

（現在のところなし）

[0.1.0] - 2026-03-29
--------------------

追加 (Added)
- パッケージ初版を公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本モジュールとパブリックAPI：
  - kabusys.__init__ により、data / strategy / execution / monitoring を公開。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルート (.git または pyproject.toml を起点) を探索して .env / .env.local を読み込む。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env を上書き（OS 環境変数は保護）。
  - .env パーサの強化:
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理などに対応。
  - 必須環境変数取得用の _require() を提供（未設定時は ValueError）。
  - 設定プロパティを提供（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path 等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）および is_live / is_paper / is_dev ヘルパー。

- AI 関連 (src/kabusys/ai)
  - ニュースNLP スコアリング (news_nlp.py):
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に書き込む。
    - タイムウィンドウ計算 calc_news_window(target_date)（JST を基準に UTC へ変換）を追加。
    - バッチ処理: 最大 20 銘柄／API コール、1銘柄あたり記事数・文字数のトリムでトークン肥大化対策。
    - JSON Mode のレスポンス検証・パース機能（_validate_and_extract）。部分失敗時のフォールバックやログ出力。
    - リトライと指数バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）。
    - DuckDB 0.10 の executemany の空リスト制約に対する対策（空チェック）。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定 (regime_detector.py):
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime に書き込む。
    - マクロ記事の抽出 (_fetch_macro_news)、ma200 比率計算 (_calc_ma200_ratio)、LLM 呼び出しとリトライ処理（_score_macro）を実装。
    - OpenAI 呼び出しは専用の内部実装（news_nlp と共有しない）でモジュール結合を避ける設計。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ、DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で処理。
    - ルックアヘッドバイアス対策（datetime.today()/date.today()をスコープ外で参照しない、DB クエリは target_date 未満のデータのみを使用）。

- リサーチ（src/kabusys/research）
  - factor_research.py:
    - calc_momentum(conn, target_date)：1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を算出。
    - calc_volatility(conn, target_date)：20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率等を算出。true_range の NULL 伝播を考慮。
    - calc_value(conn, target_date)：raw_financials から最新財務を取得し PER・ROE を計算。
    - 各関数は prices_daily / raw_financials のみに依存し、本番発注API等にはアクセスしない設計。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None)：複数ホライズンの将来リターンを一度に取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンのランク相関（IC）を実装（同順位は平均ランク扱い、3 件未満は None）。
    - rank(values)：同順位の平均ランク処理と丸めによる ties 対策を実装。
    - factor_summary(records, columns)：count/mean/std/min/max/median を算出する統計サマリー関数。
    - 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで完結する実装方針。

- データ (src/kabusys/data)
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar）機能を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - calendar_update_job(conn, lookahead_days=90)：J-Quants API（jquants_client）からカレンダーを差分取得して market_calendar を冪等で更新。バックフィル、健全性チェックを実装。
    - カレンダーデータが未取得の場合は曜日ベース（平日）のフォールバックを取り扱い、DB がまばらな場合も一貫した判定ができるように設計。
  - pipeline.py / etl.py:
    - ETL のインターフェースと ETLResult データクラスを追加（etl.py では ETLResult を再エクスポート）。
    - ETLResult に品質チェック結果 quality_issues（QualityIssue の配列）と errors を含める。has_errors / has_quality_errors / to_dict を提供。
    - pipeline の内部ユーティリティ: テーブル存在確認、最大日付取得、差分取得のための日付調整など。
    - ETL の設計：差分更新、保存は jquants_client の save_* を使用し冪等保存、品質チェックは Fail-Fast にせず呼び出し元で判断可能にする。

変更 (Changed)
- ルックアヘッドバイアス対策を全体方針として採用（AI / research / news などのモジュールで date 時刻取得を外部引数に依存）。
- OpenAI 呼び出し部分は gpt-4o-mini を使い JSON Mode を前提とした設計に統一。

修正 (Fixed)
- DuckDB の executemany 空リスト制約（0.10）への対策を実装（空リスト送信回避）。
- API レスポンスのパース失敗や非致命的エラー時のフェイルセーフ挙動（0.0 のスコアやスキップ）を追加して堅牢性を向上。

注記（Notes）
- OpenAI 連携：
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とする。未設定時は ValueError を送出。
  - レート制限やサーバー側の一時エラーには指数バックオフでリトライする設計。ただし最終的に失敗した場合は該当チャンク／記事をスキップして処理を継続する（フェイルセーフ）。
  - テスト容易性のため、内部の _call_openai_api をモック可能とした。

- データベース操作：
  - DuckDB を想定（DuckDBPyConnection 型注釈）。
  - 主要な書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、例外時は ROLLBACK を試行してエラーを上位に伝搬。
  - 一部処理は SQL 内でウィンドウ関数（ROW_NUMBER, LAG, LEAD, AVG OVER 等）を多用。

既知の制限 / 今後の改善案
- 現フェーズでは PBR・配当利回り等のバリューファクターは未実装（calc_value に注記あり）。
- OpenAI モデル名・パラメータは固定（gpt-4o-mini / temperature=0 等）。将来的に動的に設定可能にする余地あり。
- calendar_update_job と ETL の jquants_client 呼び出しは外部依存（API 側の仕様変更に影響される）。
- news_nlp の JSON パースにおいて、LLM の非厳格出力に対する防御（前後の余計なテキスト除去）は入れているが、さらなる堅牢化が望ましい。

脚注
- 初回リリースであり、上記はコードから推測可能な機能・設計・フェイルセーフをまとめたものです。実運用前に実際の環境（APIキー、DB、J-Quants 連携、Slack 連携等）で十分なテストを行ってください。
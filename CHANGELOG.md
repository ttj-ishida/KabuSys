Keep a Changelog に準拠した形式で、コードベースから推測した初回リリースの変更履歴を日本語で作成しました。

CHANGELOG.md
=============
すべての変更は https://keepachangelog.com/ja/ に準拠しています。

Unreleased
----------

なし

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"
    - __all__ で主要サブパッケージ（data, research, ai, ...）を公開

- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）
    - export KEY=val 形式やクォート・コメントの扱いに対応したパーサー実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
    - Settings クラスを公開:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須環境変数取得メソッド（未設定時は ValueError）
      - kabu_api_base_url, duckdb_path, sqlite_path のデフォルト値
      - KABUSYS_ENV / LOG_LEVEL の入力バリデーション（有効値セットを定義）
      - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュース NLP（センチメントスコアリング）
  - src/kabusys/ai/news_nlp.py
    - score_news(conn, target_date, api_key=None): raw_news を銘柄ごとに集約して OpenAI に送信し ai_scores に書き込むパイプラインを実装
    - タイムウィンドウ計算 calc_news_window（JST ベースの前日15:00〜当日08:30 を UTC に変換）
    - 銘柄ごとの記事集約 (_fetch_articles)、1 チャンク最大20銘柄のバッチ送信、トークン肥大対策（記事数／文字数制限）
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）
    - JSON Mode を利用したレスポンス検証（冗長テキストが混入するケースの復元ロジック含む）
    - レスポンス検証とスコアクリップ（±1.0）、部分失敗に耐える idempotent な DB 書き込み（DELETE → INSERT）
    - テスト用に _call_openai_api を差し替え可能な設計

- 市場レジーム判定
  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None): ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込む
    - ma200_ratio 計算（200日分の終値、データ不足時は中立値 1.0）
    - マクロキーワードでフィルタしたニュースタイトル抽出 (_fetch_macro_news)
    - OpenAI による macro_sentiment 評価（gpt-4o-mini を想定）、リトライ／フォールバック（失敗時 macro_sentiment=0.0）
    - 重み付け合成（70% MA, 30% マクロ）と閾値によるラベル付与（bull / neutral / bear）
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK の扱い）

- データ基盤ユーティリティ
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーを扱うユーティリティ群:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でのフォールバック実装
    - calendar_update_job(conn, lookahead_days): J-Quants（jquants_client 経由）から差分取得して market_calendar を冪等更新、バックフィル・健全性チェックを実装
    - 最大探索日数やバックフィル日数、先読み日数などの定数を定義し安全性を確保

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult dataclass を導入（ETL 結果の構造化: 取得数・保存数・品質問題・エラー等）
    - _table_exists / _get_max_date などの DB ヘルパー
    - 差分更新・バックフィル・品質チェック方針に沿った設計（ドキュメント化）

  - src/kabusys/data/__init__.py
    - ETLResult の再エクスポート（kabusys.data.ETLResult）

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 の乖離率
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER, ROE を計算（EPS 無しは None）
    - データ不足時に None を返す設計、DuckDB SQL を中心に実装（外部 API へはアクセスしない）

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons): 将来リターンの計算（複数ホライズンを同一クエリで取得）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算、3 サンプル未満では None
    - rank(values): 平均ランク（同順位は平均ランク）
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリー
    - すべて標準ライブラリ + DuckDB で動作する設計（pandas 等に依存しない）

- テスト・堅牢性向上のための設計上の注意点（コード中ドキュメント）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date を引数で受ける）
  - OpenAI 呼び出しや外部 API の失敗時はフェイルセーフ（例外を上位に上げないケース・フォールバック値を用意）
  - DuckDB の互換性ワークアラウンド（executemany に空リストを渡さない等）
  - idempotent な DB 書き込み（DELETE→INSERT、ON CONFLICT の利用想定）
  - OpenAI の JSON モードでのレスポンスパースの堅牢化（前後余分テキストの切り出し等）
  - リトライ戦略（指数バックオフ、リトライ対象の明確化）

Changed
- 初回リリースのため該当なし（今後のリリースで差分を記載）

Fixed
- 初回リリースのため該当なし

Security
- 環境変数（API キー等）は必須とし、未設定時は明示的にエラーを返す箇所を設置（OpenAI, Slack, J-Quants 等）
- .env 自動ロード時に OS 環境変数を protected として上書きを抑止する仕様を採用

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini を想定した実装で JSON Mode（response_format）を使用しているが、実運用では利用する SDK/API の挙動変化に注意が必要
- ai モジュールの挙動は外部 API に依存するため、テストでは _call_openai_api の差し替えやモックを推奨
- DuckDB のバージョン差異による SQL バインド挙動（リストバインド等）に対する互換性対策を実装しているが、環境依存テストが必要

Authors
- コードベース（初期実装）に基づく推測で作成

もし特定の変更点（例: リリース日を別にする、より詳細な注釈、セマンティックバージョニングに関する方針）を追加したい場合は指示してください。
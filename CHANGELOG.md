CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
公開バージョンはセマンティックバージョニングを使用します。

[Unreleased]
-------------

（現時点では未公開の追加変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージトップ:
    - src/kabusys/__init__.py によるパッケージ公開とバージョン定義。
  - 設定・環境変数管理 (src/kabusys/config.py):
    - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
      - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサーは export 構文、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを提供し、必須項目は取得時に ValueError を送出して明示的に検出。
      - バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）を検証。
      - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）は Path として取得。
  - AI 関連 (src/kabusys/ai/*):
    - ニュース NLP スコアリング (news_nlp.py)
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を計算。
      - リクエストは銘柄を最大20件のチャンクでバッチ送信。JSON モードで応答を受け取り、バリデーションを実施。
      - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。
      - スコアは ±1.0 にクリップ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
      - テスト容易性: _call_openai_api を patch して差し替え可能。
      - タイムウィンドウ計算（JST ベース）: calc_news_window を提供（ルックアヘッドバイアス対策）。
    - 市場レジーム判定 (regime_detector.py)
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
      - OpenAI 呼び出しでのリトライ/フォールバックや、API 失敗時には macro_sentiment=0.0 を適用するフェイルセーフを実装。
      - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
      - テスト容易性: _call_openai_api を patch で差し替え可能、api_key を引数注入可能。
  - データプラットフォーム (src/kabusys/data/*):
    - マーケットカレンダー管理 (calendar_management.py)
      - market_calendar テーブルを元に営業日判定、次/前営業日取得、期間内営業日列挙、SQ日判定等のユーティリティを提供。
      - DB が未取得の場合は曜日ベースのフォールバック（週末除外）を採用。
      - カレンダー差分取得の夜間ジョブ calendar_update_job を実装（J-Quants クライアントを利用）。
      - バックフィル、先読み、健全性チェック（将来日付が過度に遠い場合のスキップ）を実装。
    - ETL パイプライン (pipeline.py, etl.py)
      - ETLResult データクラスによる実行結果表現。
      - 差分更新、backfill、保存（jquants_client の save_* を想定した冪等保存）および品質チェックの設計方針を実装。
      - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
    - ETL の公開インターフェースを etl モジュールで再エクスポート。
  - リサーチ・ファクター (src/kabusys/research/*):
    - factor_research.py
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）等のファクター計算を実装。
      - DuckDB による SQL ベースの実装で prices_daily / raw_financials を参照。
      - データ不足時は None を返すなどの堅牢な挙動。
    - feature_exploration.py
      - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman ランク相関）calc_ic、rank（同順位の平均ランク対応）、factor_summary（基本統計量）を実装。
      - pandas 等の外部ライブラリに依存せず標準ライブラリで実装。
  - 共通設計/実装上の注意
    - ルックアヘッドバイアス防止: datetime.today()/date.today() をモデル計算内部で直接参照しない設計（関数に target_date を注入）。
    - OpenAI SDK 呼び出しは明示的にタイムアウト・温度設定・JSON response_format を指定。
    - API 呼び出し部は明示的にテストで差し替え可能にしている（_call_openai_api を patch）。
    - DuckDB 0.10 の挙動に配慮（executemany に空リストを渡さない等の互換性処理）。
    - 主要な DB 書き込みは冪等処理（DELETE → INSERT や ON CONFLICT）で実施し、失敗時は ROLLBACK を試行。
    - ロギングを各処理で充実させ、失敗時は警告/例外ログで状況を判別できるようにしている。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出して明示的に検出。

Notes / Known issues
- OpenAI SDK の例外ハンドリングは v1 系の挙動（APIError に status_code を持つ場合がある）に依存する実装部分があるため、将来の SDK 変更に注意が必要。
- DuckDB のバージョン差異（特に executemany の空リストバインドの扱い）に配慮した回避コードを含むが、実環境での互換性検証を推奨。
- gpt-4o-mini を使用するプロンプトは厳密な JSON を期待する設計のため、モデルの応答形式変更や API の挙動変化があるとパースエラーとなり得る。失敗時は安全側（スコア 0.0 / スキップ）で処理を続行するが、品質向上のため応答バリデーションとログ監視を推奨。

開発者向けメモ
- 環境変数自動読み込みを無効化してユニットテストを実行するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのテストは各モジュールの _call_openai_api を unittest.mock.patch で差し替えることで HTTP を行わずに実行可能です。
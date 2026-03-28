Keep a Changelog に準拠した CHANGELOG.md（日本語）
※ 本ファイルは与えられたコードベースから推測して作成しています。

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under Semantic Versioning.

Unreleased
----------
- （なし）

[0.1.0] - 2026-03-28
--------------------
Added
- 初回リリース: kabusys パッケージ v0.1.0 を提供。
- パッケージ公開情報:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義（strategy/execution/monitoring は API 表示上含まれるが、今回のコード群では実装ファイルは含まれていません）。
- 環境設定/設定管理:
  - src/kabusys/config.py に Settings クラスを実装。環境変数から設定を取得するユーティリティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - .env 自動読み込み機能を実装:
    - リポジトリルートの検出（.git または pyproject.toml を探索）により .env と .env.local を自動読み込み。
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等を考慮した独自パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
    - OS 環境変数を保護する protected パラメータを用いた読み込み順序（OS > .env.local > .env）。
  - 設定検証: KABUSYS_ENV, LOG_LEVEL の許容値検査や必須キー未設定時に ValueError を投げる _require を実装。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を Path として返すプロパティを提供。
- AI 関連機能:
  - ニュース NLP スコアリング:
    - src/kabusys/ai/news_nlp.py に score_news を実装。raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルに書き込む機能。
    - タイムウィンドウ calc_news_window を実装（前日 15:00 JST ～ 当日 08:30 JST を対象、内部は UTC naive datetime を使用）。
    - 1 銘柄あたりの最大記事数・最大文字数トリミング、チャンク毎の最大処理銘柄数（_BATCH_SIZE=20）を設定。
    - OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用、レスポンスのバリデーション（results 配列、code と score の検証）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する再試行（指数バックオフ）ロジックを実装。失敗時はスキップして処理を継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で部分失敗時に他コードの既存データを保護。DuckDB executemany の空パラメータ制約に対する対策あり。
    - テスト容易性のため OpenAI 呼び出し箇所（_call_openai_api）を patch 可能に設計。
  - 市場レジーム判定:
    - src/kabusys/ai/regime_detector.py に score_regime を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - MA200 比率計算（ルックアヘッド防止のため target_date 未満のみ使用、データ不足時は中立 1.0 を返す）。
    - マクロキーワードで raw_news をフィルタしタイトルを抽出、OpenAI によるセンチメント評価を行う。API 失敗時は macro_sentiment = 0.0 で継続。
    - スコア合成・閾値処理・market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼び出しに対するリトライ・エラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError の 5xx 判定）を実装。
- データプラットフォーム（Data）:
  - src/kabusys/data/pipeline.py と src/kabusys/data/etl.py:
    - ETLResult データクラスを実装。ETL のフェッチ数・保存数・品質チェック結果・エラー集計を保持し、to_dict でシリアライズ可能。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱いなど）をコード上に明記。
    - DuckDB のテーブル最大日付取得等のユーティリティを実装。
  - カレンダー管理:
    - src/kabusys/data/calendar_management.py に market_calendar を扱う一連のユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装し、market_calendar がなければ曜日ベースでフォールバック。
    - calendar_update_job を実装し J-Quants クライアント（jquants_client）から差分取得・冪等保存（ON CONFLICT 相当）を行う。バックフィル、先読み、健全性チェックを実装。
- リサーチ機能（Research）:
  - src/kabusys/research/factor_research.py:
    - calc_momentum（1M/3M/6M リターン、200日 MA 乖離）、calc_volatility（20日 ATR・相対 ATR・平均売買代金・出来高比率）、calc_value（PER/ROE）を実装。DuckDB 上の SQL を利用して効率的に計算。
    - データ不足時の None 扱いやスキャン範囲バッファ等、現実的な営業日考慮を実装。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターンを一度のクエリで取得）、calc_ic（スピアマンのランク相関による IC 計算）、factor_summary（基本統計量の算出）、rank（同順位は平均ランク）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
  - reexports: src/kabusys/research/__init__.py で主要関数をまとめて公開。
- ロギング・設計方針・品質:
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照するロジックを避け、target_date を明示的に受け取る設計を徹底。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等に実装し、ROLLBACK 失敗時の警告ログを出力。
  - OpenAI 周りは JSON モード利用・厳密なレスポンス検証・パース失敗・未知コードの無視等、頑健な取り扱い。
  - テスト容易性を配慮し、API 呼び出し箇所をパッチ可能にしてユニットテストで差し替えられるようになっている。
- 依存・外部 API:
  - DuckDB を主要なローカルデータベースとして想定。
  - OpenAI SDK（OpenAI クラス）を使用。モデルは gpt-4o-mini を既定。
  - J-Quants クライアント（jquants_client）をデータ取得に利用する想定（calendar_management や pipeline で使用）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- API キー（OpenAI 等）が未設定の場合は ValueError を投げて明示的に失敗する実装。自動でのキー保存処理や平文保管は行わない設計。

Notes / Known limitations
- strategy / execution / monitoring モジュールはパッケージの __all__ に含まれているが、このコードスナップショットでは具体的実装ファイルが含まれていません（将来的な追加対象）。
- OpenAI への実際の呼び出しはネットワーク依存であり、API レスポンス形式や SDK の変更によりハンドリングの修正が必要になる可能性があります。
- DuckDB executemany の空リストバインドに関する暫定対応が含まれているため、環境の DuckDB バージョン差異に注意してください。

今後の予定（推測）
- strategy / execution / monitoring モジュールの具体実装追加（売買戦略の定義・注文実行・監視・アラート等）。
- テストカバレッジ拡充（外部 API のモックを用いたユニット/統合テスト）。
- ドキュメント（Usage、データスキーマ、運用手順）の追加。

----- End of CHANGELOG -----
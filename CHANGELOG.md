Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

なし

[0.1.0] - 2026-04-03
--------------------

Added
- 初回公開: KabuSys (日本株自動売買システム) の v0.1.0 を追加。
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__="0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して決定（CWD に依存しない）。
  - .env のパース機構を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理、空行/コメント行スキップに対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベースパス / 監視閾値 / システム設定などをプロパティ経由で取得。
  - env (KABUSYS_ENV) と log_level (LOG_LEVEL) の値検証（許容値チェック）を実装。
  - 必須環境変数未設定時には ValueError を送出する _require を提供。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を基に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、センチメント（ai_score）を ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST の仕様（UTC へ変換）を calc_news_window で算出。
    - バッチサイズ、文字数上限、記事数上限を導入しトークン肥大化を抑制。
    - JSON Mode を想定したレスポンス検証と堅牢パース（前後ノイズから {} を抽出する復元ロジック含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - 部分失敗を考慮した idempotent な DB 書込み（対象コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため _call_openai_api などの内部関数を差し替え可能に設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロキーワードによる raw_news フィルタ、最大記事数制限、OpenAI（gpt-4o-mini）呼出し、リトライ処理、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - DB へは冪等的に BEGIN / DELETE / INSERT / COMMIT ロジックで保存。失敗時は ROLLBACK を試行。
- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。データ不足時は None を返す仕様。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
    - DuckDB SQL ウィンドウ関数を多用し、高速に一括計算する実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）先の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3 件）では None を返す。
    - rank: 同順位は平均ランクとするランク変換。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティの公開（__init__.py で必要関数を再エクスポート）。
- データ（Data）モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理ロジックを実装。market_calendar テーブルを参照して営業日判定（is_trading_day）、翌前営業日の検索（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）、SQ 日判定を提供。
    - market_calendar が未取得のケースへの曜日ベースのフォールバック実装（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理。バックフィル・健全性チェックあり。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラー一覧などを保持）。etl.py で ETLResult を公開。
    - pipeline モジュールは差分取得、idempotent 保存（jquants_client を利用）、品質チェック（quality モジュール）を想定した設計。backfill, カレンダー先読み等のパラメータを考慮。
  - DuckDB を前提とした SQL 実装と互換性配慮（executemany の空リスト回避など）。
- ドキュメント化:
  - 各モジュールに処理フロー、設計方針、注意点（ルックアヘッドバイアス回避、テスト容易性、フェイルセーフ等）を詳細な docstring として追加。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Notes / 補足
- OpenAI API 呼び出しでは gpt-4o-mini を想定し、JSON Mode のレスポンスを期待する実装になっています。実運用では OPENAI_API_KEY の設定が必要です（Settings 経由または各関数の api_key 引数）。
- DB 操作は DuckDB 接続を受け取る設計です。テストでは DuckDB の in-memory 接続やモックを利用して検証できます。
- 一部外部クライアント（jquants_client 等）への依存があるため、これらのクライアント実装に応じて設定・モックを用意してください。

Authors
- KabuSys 開発チーム（コード内 docstring に基づく実装説明を含む）

[0.1.0]: https://example.com/releases/0.1.0
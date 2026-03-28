CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠します。

履歴
----

### [0.1.0] - 2026-03-28
初回リリース。

Added
-----
- パッケージの基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージの公開インターフェースを定義（src/kabusys/__init__.py: data, strategy, execution, monitoring を __all__ に設定）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない動作。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮。
  - 環境変数保護機能:
    - OS 環境変数を protected として .env.local での上書きを制御。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabu ステーション / Slack / DB パスなどのプロパティを環境変数から取得。
    - 必須変数未設定時は ValueError を送出する _require 実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実施（有効値セットを定義）。
    - duckdb/sqlite のデフォルトパス設定。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルを集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - ニュース収集ウィンドウの計算（JST 前日15:00〜当日08:30 → UTC に変換）を calc_news_window で実装。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）と 1 銘柄あたり最大記事数/文字数でトリムする仕組みを実装。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対して指数的バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results の検証、コード整合性、数値チェック）とスコアの ±1.0 クリップ。
    - DuckDB 0.10 の executemany の空リスト制約を考慮した安全な DB 書き込み（DELETE→INSERT、部分失敗時の保護）。
    - score_news(conn, target_date, api_key=None) を公開（成功時は書込銘柄数を返す）。API キー未設定時は ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - MA200 乖離計算でルックアヘッドを防止（target_date 未満のデータのみ使用）、データ不足時は中立（1.0）にフォールバック。
    - マクロニュースは news_nlp.calc_news_window によるウィンドウで抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを期待。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - API 呼び出しはモジュール単位で独立した実装（テスト時はパッチ可能）。
    - score_regime(conn, target_date, api_key=None) を公開。DB への冪等（BEGIN / DELETE / INSERT / COMMIT）書き込みを行う。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日）を使用し、一貫性を担保。
    - 最大探索幅 (_MAX_SEARCH_DAYS) を設定して無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90) で J-Quants API（jquants_client）から差分取得して保存するバッチ処理を実装。バックフィル、健全性チェック、例外ハンドリングを含む。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETL の公開インターフェースとして ETLResult を定義（src/kabusys/data/etl.py で再エクスポート）。
    - ETLResult は取得/保存件数、品質チェック結果（quality.QualityIssue）、エラーメッセージ等を保持。has_errors / has_quality_errors / to_dict を実装。
    - 差分取得・バックフィル・品質チェックのための内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
    - デフォルトのバックフィル日数やカレンダー先読みなどの定数を定義。

- 研究（research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - 全関数は DuckDB 内の prices_daily / raw_financials を参照し、外部 API にアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターン（LEAD を利用）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。十分なサンプルがなければ None を返す。
    - rank(values): 平均ランク（同順位は平均）を返すヘルパー。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー機能。
  - research パッケージは主要関数を __all__ で公開。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- 環境変数の取り扱いに注意:
  - OPENAI_API_KEY 等の秘密情報は環境変数で提供する想定。自動 .env 読み込みは無効化可能。

Notes / Implementation details
------------------------------
- ルックアヘッドバイアス対策:
  - AI スコア算出・レジーム算出・ETL のすべてで datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える方式を採用しています。
- OpenAI 呼び出しの堅牢性:
  - 一時エラーは指数バックオフで再試行し、最終的に失敗した場合は安全側のデフォルト（ニュース: スコア未取得扱い / レジーム: macro_sentiment=0.0）で継続します。致命例外は上位に伝播。
- DuckDB 互換性考慮:
  - executemany に空リストを渡すと失敗するバージョン（例: DuckDB 0.10）への対処を実装（事前チェック）。
- モジュール分離・テスト性:
  - OpenAI 呼び出しはモジュール内のラッパー関数になっており、unittest.mock.patch で差し替え可能（テスト容易性を確保）。
- デフォルトモデル:
  - gpt-4o-mini をデフォルトの LLM モデルとして使用（news_nlp / regime_detector）。

既知の制約 / TODO
-----------------
- 一部モジュールは外部クライアント（jquants_client）や quality モジュールに依存しており、それらの実装が必要。
- 現時点で PBR・配当利回りなどのバリューファクターは未実装（calc_value の Note）。
- strategy / execution / monitoring パッケージ本体の実装はこのコードスニペットに含まれていない（将来の追加予定）。

----

（注）リリース内容はソースコードの実装から推測して作成しています。実際のリリースノートへ反映する際は、開発チームの変更履歴やコミットログと照合してください。
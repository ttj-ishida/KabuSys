CHANGELOG
=========

すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" — and is maintained for humans and machines.

Unreleased
----------
- （今後の予定欄。ここには次回リリースでの変更を記載してください。）

[0.1.0] - 2026-04-02
--------------------
初回公開リリース。パッケージの基盤機能（設定管理、データ ETL / カレンダー管理、研究用ファクター計算、ニュース / レジームの AI スコアリング 等）を実装しました。

Added
- パッケージ基盤
  - パッケージバージョンを 0.1.0 として設定（src/kabusys/__init__.py）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を追加。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルート（.git または pyproject.toml）を探索して自動ロードを行う。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーは export プレフィックス対応、クォートとエスケープシーケンス処理、インラインコメントの取り扱いを考慮。
  - 環境変数保護（既存 OS 環境変数を上書きしない／保護する仕組み）を実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）等をプロパティとして取得できるようにした。無効値は ValueError で通知。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを取得して ai_scores テーブルへ保存する機能を実装。
    - バッチサイズ 20、1 銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を導入してトークン肥大化を防止。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフによるリトライ処理を実装。部分失敗時に既存スコアを保護するため、書き込みは該当コードのみ置換（DELETE → INSERT）。
    - レスポンスの厳密なバリデーションと ±1.0 でのクリップを実装。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能（unittest.mock.patch を想定）。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）で算出し、ルックアヘッドバイアスを避ける設計。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする機能を実装。
    - OpenAI 呼び出しは専有実装を使用し、API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを導入。
    - MA200 の計算は target_date 未満のデータのみを参照（ルックアヘッド排除）。データ不足時は中立値（1.0）を使用して安全に処理。
    - リトライ・バックオフとエラーハンドリングを備える。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を基にした営業日判定・翌前営業日取得・期間内営業日リスト取得・SQ 判定等を実装。
    - market_calendar が未取得のときは曜日（週末）をフォールバックとして扱い、一貫性を保つロジックを提供。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・バックフィル・冪等保存を行う。健全性チェック（将来日付の異常検出）を追加。

  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装して ETL の集計・品質情報・エラーを構造化して返す。
    - 差分ロード・backfill・品質チェック（quality モジュールと連携）を想定した ETL の設計を実装（詳細は docstring）。
    - etl.py で ETLResult を再エクスポート。

- 研究用モジュール（src/kabusys/research）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 偏差）、Volatility（20日 ATR 等）、Value（PER / ROE）等のファクター計算関数を実装。
    - DuckDB を用いた SQL ベース計算で、prices_daily / raw_financials のみ参照。結果は辞書リストとして返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。外部依存を持たず標準ライブラリで実装。
  - research.__init__ で便利関数を再エクスポート（zscore_normalize 等）。

Changed
- （初回リリースにつき、過去リリースからの「変更」はありません。）

Fixed
- （初回リリースにつき、過去バグ修正履歴はありません。）

Security
- 設定取得時に必須項目が未設定の場合は明示的に ValueError を送出して安全に失敗するように実装（API キー・Slack トークン等）。
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（.env が既存の OS 環境変数を不用意に上書きしない）。

Notes / Known limitations
- OpenAI（gpt-4o-mini）利用
  - OPENAI_API_KEY を環境変数で利用。api_key 引数で明示的に注入可能。未設定時は ValueError を送出する。
  - LLM 呼び出しは外部サービスに依存するため、API エラー時はフェイルセーフ（0.0 フォールバックやスキップ）する設計。ただし、外部サービスの可用性により一部処理がスキップされる可能性がある。
- DuckDB の互換性
  - DuckDB の executemany が空リストを受け付けない制約を考慮して、挿入前に params の空チェックを行っている。
- ルックアヘッドバイアス対策
  - score_news / score_regime 等の関数は、内部で date.today() を参照しない設計（全て target_date を明示的に与える）で、ルックアヘッドを避けるよう配慮している。
- テスト容易性
  - OpenAI 呼び出し部は内部関数をパッチ差し替え可能にしているため、ユニットテストでのモックが容易。

Migration / 運用メモ
- 主要な環境変数名:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY
- 自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトの DB ファイルパスは data/kabusys.duckdb（DuckDB）および data/monitoring.db（SQLite）です。

Contributing
- バグ報告・機能要望は issue を作成してください。設計方針やドキュメントに基づく実装上の判断をした箇所には docstring に根拠を残してありますので、参照のうえ議論いただけるとスムーズです。

----- 
（注）この CHANGELOG はリポジトリ内のソースコード記述・ docstring から推測して作成しています。実際のコミット単位の変更履歴が必要な場合は git の履歴から生成してください。
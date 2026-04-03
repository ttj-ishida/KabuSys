# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL（J-Quants からのデータ取り込み）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログスキーマなど、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム／研究プラットフォームの共通ユーティリティを集めたパッケージです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ベースのニュース収集と OpenAI による銘柄別センチメントスコアリング
- ETF とマクロニュースを組み合わせた「市場レジーム」判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order → execution のトレース可能なスキーマ）
- DuckDB を使ったローカルデータベース操作のユーティリティ

設計上の特徴:
- ルックアヘッドバイアスを避けるため、date 引数ベースで処理（date.today() に依存しない箇所が多い）
- 冪等性：DB 書き込みは原則 ON CONFLICT / DELETE→INSERT などで上書き可能
- フェイルセーフ：外部 API（OpenAI / J-Quants）失敗時は可能な範囲で継続して動作する

---

## 主な機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：fetch / save（差分・ページネーション・リトライ対応）
- ニュース関連
  - RSS 収集（kabusys.data.news_collector）: URL 正規化／SSRF 対策／XML 防御
  - ニュース NLP（kabusys.ai.news_nlp）: OpenAI を用いた銘柄別センチメントスコア（ai_scores へ保存）
- レジーム判定
  - kabusys.ai.regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM センチメントを合成して market_regime を更新
- 研究・ファクター
  - kabusys.research.factor_research: calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - 共通統計ユーティリティ: kabusys.data.stats.zscore_normalize
- データ品質
  - kabusys.data.quality: 欠損・スパイク・重複・日付不整合チェック、QualityIssue 型で結果を返す
- 監査ログ（トレーサビリティ）
  - kabusys.data.audit.init_audit_db / init_audit_schema：監査用 DuckDB スキーマ初期化
- 設定管理
  - kabusys.config.Settings: 環境変数 / .env(.local) 自動ロード（プロジェクトルート基準）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈や構文で Python 3.10+ を想定）
- DuckDB、OpenAI SDK、defusedxml 等のパッケージが必要

推奨インストール例:

1. 仮想環境作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。
   また、標準ライブラリの urllib を多用しているため追加 HTTP ライブラリは不要です。）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須：発注系を使う場合）
- OPENAI_API_KEY: OpenAI API キー（news/regime の実行に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/Mem/Disk 閾値 など

.env の自動読み込みルール:
- OS 環境変数 > .env.local > .env の順に優先
- .env の行解析は shell 風（export KEY=val、引用符、コメント考慮）
- プロジェクトルートが見つからない場合は自動読み込みをスキップ

---

## 使い方（簡単な使用例）

以下はパイソン REPL やスクリプトから呼び出す例です。

1) DuckDB 接続を作って日次 ETL を実行する
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

2) ニューススコアリングを行う
- 必要: OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
- 例:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026,3,20))
  - print("書き込み銘柄数:", n_written)

score_news は raw_news / news_symbols テーブルを参照し ai_scores を更新します。

3) 市場レジームを判定する
- 例:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20))

regime_detector は ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime を更新します。

4) 監査用 DB 初期化
- 例:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn は初期化済みの DuckDB 接続

5) jquants_client を直接使ってデータ取得
- 例:
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  - quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,31))

注意点:
- OpenAI への呼び出しはレスポンス形式 (JSON mode) を期待しています。API の制約や課金設定に注意してください。
- J-Quants API はレート制限を守る実装になっていますが、自身の契約や運用に合わせた制御を行ってください。

---

## ディレクトリ構成

主要なファイル・モジュールの構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し、ai_scores 書き込み
    - regime_detector.py      — 市場レジーム判定（1321 MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - etl.py                  — ETL の再エクスポート（ETLResult）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック（QualityIssue）
    - audit.py                — 監査ログスキーマ / 初期化
    - jquants_client.py       — J-Quants API クライアント（fetch/save 等）
    - news_collector.py       — RSS 収集と前処理
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等

この README に記載していない補助モジュール（execution/monitoring/strategy 等）はパッケージ API の一部として __all__ に含まれますが、上記がコアのデータ・研究・AI 周りの主要部分です。

---

## 注意事項と運用上のポイント

- 環境変数の管理:
  - .env/.env.local をプロジェクトルートに置くと自動で読み込まれます。テストや CI で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Secret 管理:
  - API キー（J-Quants / OpenAI / kabu）や LINE トークンは安全に管理してください。リポジトリへコミットしないでください。
- API のエラーハンドリング:
  - J-Quants クライアントと OpenAI 呼び出しはリトライやバックオフを含みますが、運用ではレートや課金制限に注意して下さい。
- DuckDB のバージョン依存:
  - 一部実装は DuckDB の executemany の振る舞い（空リスト渡し不可等）を考慮しています。DuckDB バージョンの互換性には注意してください。
- ルックアヘッド対策:
  - 多くの関数が内部で date 引数を受け取り、現在日時を参照しない設計になっています。バックテスト用途でもその点に留意してください。

---

もし README に追加したい具体的な使用例（CLI スクリプト、docker-compose、CI ワークフロー、サンプル .env.example）や、依存関係ファイル（requirements.txt / pyproject.toml）があれば提供してください。README をそれに合わせて拡張します。
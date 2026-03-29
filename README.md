# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETF / 株価データのETL、ニュースの収集・NLP解析、ファクター計算、監査ログ・発注管理などの機能を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス回避」「DuckDBでの冪等保存」「外部API呼び出しの堅牢化（リトライ・レート制限）」です。

---

## 機能一覧

- 環境変数／設定管理
  - .env 自動読み込み（プロジェクトルート基準）、自動無効化フラグあり
- データ取得（J-Quants 経由）
  - 株価日足（OHLCV）取得・保存（ページネーション・冪等）
  - 財務データ取得・保存（四半期）
  - JPXマーケットカレンダー取得・保存
  - API レート制御・リトライ・自動トークンリフレッシュ実装
- ETL
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次パイプライン入口 run_daily_etl
- ニュース収集
  - RSS 取得、URL 正規化、SSRF対策（リダイレクト検査・プライベートIP拒否）、前処理、raw_news への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメントスコアリング（gpt-4o-mini、JSON mode）
  - チャンク化・リトライ・レスポンス検証・スコアクリップ
  - 関数: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200日MA乖離（70%）とマクロニュース LLMセンチメント（30%）を加重合成
  - 関数: kabusys.ai.regime_detector.score_regime
- リサーチ／ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン、IC 計算、統計サマリ等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - init_audit_schema / init_audit_db による初期化
- 汎用統計ユーティリティ
  - Zスコア正規化など

---

## セットアップ手順

※ 本リポジトリは Python パッケージとして想定しています。適宜仮想環境を作成してください。

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .

2. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（およびローカル上書き `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数一覧:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (省略可; デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
     - OPENAI_API_KEY (OpenAI 呼び出しに必要)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — 動作モード
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - .env の書式は一般的な KEY=VALUE。クォートやコメント行にも対応します。

3. 必要な外部サービスの準備
   - J-Quants アカウント（refresh token）
   - OpenAI API キー（ニュース NLP / レジーム判定に使用）
   - kabuステーション（実行モジュールを使う場合）
   - Slack（通知を行う場合）

4. データディレクトリを作成（必要なら）
   - 例:
     - mkdir -p data

---

## 使い方（主要な操作例）

以下はライブラリを直接呼ぶ最小の使用例です。実行は Python スクリプト内で行います。

1. DuckDB に接続して日次 ETL を実行する
   - 例:
     - python
       - import duckdb
       - from kabusys.config import settings
       - from kabusys.data.pipeline import run_daily_etl
       - conn = duckdb.connect(str(settings.duckdb_path))
       - result = run_daily_etl(conn)
       - print(result.to_dict())

   - run_daily_etl は市場カレンダー → 株価 ETL → 財務 ETL → 品質チェック の順に実行し、ETLResult を返します。

2. ニュースセンチメントを計算して ai_scores に保存する
   - 例:
     - from datetime import date
     - import duckdb
     - from kabusys.ai.news_nlp import score_news
     - conn = duckdb.connect("data/kabusys.duckdb")
     - n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
     - print("書き込んだ銘柄数:", n_written)

   - OpenAI API キーを `api_key` 引数で渡すか、環境変数 `OPENAI_API_KEY` を設定します。
   - 空記事や記事無しの場合は LLM 呼び出しをスキップします。失敗時はフェイルセーフでスコア算出をスキップします。

3. 市場レジーム判定を実行する
   - 例:
     - from kabusys.ai.regime_detector import score_regime
     - conn = duckdb.connect("data/kabusys.duckdb")
     - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

   - 内部では 1321 の MA200 乖離とマクロニュース LLM を組み合わせます。API キー未設定時は ValueError を送出します。

4. 監査ログ用 DB を初期化する
   - 例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - # conn は監査テーブルが初期化された DuckDB 接続

5. 個別 ETL ジョブを直接呼ぶ
   - run_prices_etl / run_financials_etl / run_calendar_etl を使用して差分ETLを個別実行可能。

注記:
- すべての関数は "ルックアヘッドバイアス防止" のため、内部で date.today() のみを参照せず、呼び出し側で target_date を渡すことを推奨する設計です。
- OpenAI 呼び出しはリトライや JSON 検証を実装しており、API エラー時はスコアにフォールバック（例: 0.0）するなどのフェイルセーフを備えています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースNLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 結果の型再エクスポート
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — マーケットカレンダー管理・営業日判定
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai, data, research の内部で利用される小さなユーティリティ群が含まれます。

---

## 実装上の重要ポイント / 注意事項

- ルックアヘッドバイアスへの配慮
  - 多くのモジュールは target_date を明示的に受け取り、クエリには date < target_date や date <= target_date の扱いでルックアヘッドを防止しています。
- 冪等性
  - J-Quants データの DB 保存は ON CONFLICT DO UPDATE を利用し冪等に保存します（save_* 関数群）。
- 外部APIの堅牢化
  - J-Quants クライアントは固定間隔レートリミッター、リトライ、401 の自動リフレッシュを提供します。
  - OpenAI 呼び出しは JSON モードを利用し、429/タイムアウト/5xx で指数バックオフのリトライを行います。
- セキュリティ / 安全性
  - RSS 収集は SSRF 対策（プライベートホスト検査・リダイレクト検査）、レスポンスサイズ上限、XML パースに defusedxml を使用などを行っています。
- DuckDB 互換性
  - executemany に空リストを渡すと問題になるバージョンの対策など、DuckDB の挙動に合わせた実装上の配慮があります。

---

## 追加のヒント

- ローカル開発で環境変数読み込みを無効にするには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ログレベルは環境変数 `LOG_LEVEL` で制御できます（デフォルト INFO）。
- ETL の監査・監視は別モジュール（monitoring）に想定されています（__all__ に monitoring が含まれています）。

---

必要であれば、README に実行用の具体的な CLI コマンド例（cron での daily_etl 呼び出しスクリプト等）や .env.example のテンプレート、SQL スキーマ定義の抜粋、さらに詳細な API 使用例（関数シグネチャごとのパラメータ説明）を追加できます。どの情報を優先して追記しますか？
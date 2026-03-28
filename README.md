# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買システムのコアライブラリ群です。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、マーケットカレンダー管理、監査ログ（DuckDB）などをモジュール化して提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームの内部ライブラリ群を想定したコードベースです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダーデータの差分取得および DuckDB への保存（ETL）
- ニュースの収集と LLM（OpenAI）を用いた銘柄別／マクロのセンチメントスコア算出
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析（IC 等）
- 市場カレンダー（JPX）管理と営業日判定ユーティリティ
- 発注・約定をトレースする監査ログスキーマ（DuckDB）
- 環境変数・設定管理ユーティリティ

設計方針としては、ルックアヘッドバイアス防止、冪等性（ON CONFLICT）、フェイルセーフ（API障害時のフォールバック）、およびシンプルな依存（標準ライブラリ＋必要最低限の外部ライブラリ）を重視しています。

---

## 主な機能一覧

- data
  - J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理、営業日判定ユーティリティ
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- ai
  - ニュース NLP（銘柄別センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成 → score_regime）
  - OpenAI 呼び出しは JSON mode を利用しレスポンスのバリデーションを行う
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（スピアマン）・統計サマリー等
- utils
  - 設定管理（環境変数ロード・保護・検証: kabusys.config.Settings）
  - 統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの | 型やその他構文を使用）
- DuckDB、OpenAI SDK、defusedxml 等を利用します。

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt を作成して管理してください。

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - OPENAI_API_KEY=<your_openai_api_key>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env の書き方例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易ガイド）

以下は主要機能を Python REPL などから呼び出す例です。実運用では各処理をジョブ（cron / Airflow 等）に組み込みます。

1. DuckDB 接続の作成
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   # target_date を指定しなければ今日（日次バッチ向け）
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメントスコアの算出（銘柄別）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込んだ銘柄数: {written}")
   ```

4. 市場レジーム判定（例: ETF 1321 を使った daily 判定）
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査ログ用 DuckDB 初期化（監査専用 DB）
   ```python
   from pathlib import Path
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db(Path("data/audit.duckdb"))
   ```

6. ファクター計算 / リサーチユーティリティ
   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

   date0 = date(2026, 3, 20)
   mom = calc_momentum(conn, date0)
   val = calc_value(conn, date0)
   vol = calc_volatility(conn, date0)
   ```

注意点
- OpenAI 呼び出しを行う関数（score_news, score_regime）は OPENAI_API_KEY を参照します。api_key 引数で明示的に渡すことも可能です（テスト容易化）。
- ETL / API 呼び出しにはネットワークおよび認証トークン（J-Quants）の準備が必要です。
- run_daily_etl は各ステップでエラーハンドリングを行い、失敗しても他のステップを継続する設計です。結果は ETLResult オブジェクトで確認できます。

---

## ディレクトリ構成

主要モジュールと役割を簡潔に示します（src/kabusys をルートとする）。

- src/kabusys/
  - __init__.py                — パッケージ初期化（__version__ 等）
  - config.py                  — 環境変数 / 設定管理（.env 自動ロード・検証）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースを集約して OpenAI で銘柄スコアを生成（score_news）
    - regime_detector.py       — ETF(+LLM) で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch_ / save_ 関数）
    - pipeline.py              — ETL パイプラインと run_daily_etl（ETLResult）
    - etl.py                   — ETLResult の再エクスポート
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - news_collector.py        — RSS 収集・前処理・保存ユーティリティ
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログスキーマの初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - monitoring/ (パッケージ名のみ列挙されているが詳細実装はここに配置予定)
  - strategy/, execution/ (パッケージ列挙のみ。発注ロジック等を置く想定)

（上記はソース内の docstring や関数名から抜粋した概要です）

---

## 注意事項・運用上のヒント

- ルックアヘッドバイアス回避: 多くの関数は内部で date.today() を参照せず、target_date を明示的に受け取る設計です。バックテスト環境では target_date を正しく渡してください。
- 冪等性: J-Quants からの保存関数は ON CONFLICT を使って冪等に保存します。ETL の再実行が安全になるよう設計されています。
- OpenAI 呼び出し: レスポンスのバリデーションやリトライ処理が入っていますが、API の料金・レートに注意して使用してください。
- セキュリティ: news_collector では SSRF・XML 攻撃対策（SSRF ブロック、defusedxml、レスポンスサイズ制限など）を実装しています。外部 URL を扱う場合は引き続き注意してください。
- 環境変数の自動ロード: .env / .env.local がプロジェクトルートにあると自動読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 参考（開発者向け）

- コードドキュメントは各モジュールの docstring に詳細があります。リファクタや拡張を行う前に設計方針（Fail-Safe, 冪等性, Look-ahead 回避など）を把握してください。
- テスト時は各所で外部呼び出し（OpenAI / J-Quants / HTTP）をモックするユーティリティ呼び出し点が用意されています（例: _call_openai_api の差し替え等）。

---

ご要望があれば、README に含める具体的な .env.example、requirements.txt の候補、あるいはデプロイ手順（systemd / cron / Airflow 例）なども作成します。必要であれば教えてください。
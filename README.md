# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買基盤の一部実装です。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、および監査ログ（DuckDB）などのユーティリティ群を提供します。

主な設計方針
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を一次データストアとして利用（ETL は冪等設計）
- 外部 API 呼び出し（J-Quants / OpenAI）に対して堅牢なリトライ・レート制御を実装
- ニュース収集は SSRF や XML 攻撃対策を実装
- 監査（signal → order → execution）をトレース可能にするスキーマを提供

---

## 機能一覧

- 環境変数 / .env 自動ロード（kabusys.config）
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
  - 必須変数チェックヘルパーを提供

- データ取得・ETL（kabusys.data.jquants_client / pipeline）
  - J-Quants API から日次株価（OHLCV）、財務データ、マーケットカレンダーを取得
  - 差分更新（バックフィル対応）・ページネーション対応・レート制御・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL の統合エントリポイント（run_daily_etl）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、主キー重複、スパイク（前日比）および日付整合性チェックを実行
  - 問題は QualityIssue オブジェクトで集約

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後営業日取得 / 期間内営業日列挙 / JPX カレンダー差分更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集、正規化、SSRF/サイズ/XML 攻撃対策を実装
  - raw_news / news_symbols へ冪等保存する想定（実装の呼び出し先に依存）

- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI (gpt-4o-mini) を用いた銘柄別ニュースセンチメント算出
  - チャンク/バッチ処理、JSON モード検証、リトライ、スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離（70%）とマクロニュース LLM スコア（30%）を合成して日次レジーム判定（bull/neutral/bear）

- リサーチ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査用スキーマ定義・初期化（DuckDB）
  - init_audit_db / init_audit_schema ヘルパーを提供

---

## セットアップ手順

前提
- Python 3.10+ 推奨（型ヒントに Union | 表記を使用）
- DuckDB, OpenAI SDK, defusedxml 等の依存

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（pip）:
     - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

4. パッケージとしてインストール（開発モード）
   - pip install -e .

5. 環境変数を準備（.env）
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただしテスト等で無効化可）。
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（ニュースNLP / regime_detector を使う場合）
     - (任意) DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. 自動 .env 読み込みを無効化したい場合:
   - 環境変数: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要 API と実行例）

以下はライブラリをインポートして主要処理を呼ぶ簡単な例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュース NLP スコア生成（OpenAI API キー必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が env にある場合 api_key=None で動作
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査 DB 初期化（監査専用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- ファクター / リサーチ関数の使用例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))

  fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  ```

注意点
- OpenAI 呼び出しは外部 API なのでレートやコストに注意してください。API キーは環境変数 OPENAI_API_KEY を使用するのが簡便です。
- J-Quants API の利用には J-Quants 側のアカウントとリフレッシュトークンが必要です。
- run_daily_etl 等は内部で date.today() を使いますが、モジュールはルックアヘッドバイアスを避ける設計になっています。バッチ/テストでは target_date を明示することを推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み・取得ユーティリティ（Settings）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの LLM ベーススコアリング・バッチ処理
  - regime_detector.py
    - ETF MA200 とマクロニュースを合成する市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py
    - JPX カレンダー管理、営業日判定ヘルパー
  - etl.py
    - ETLResult エクスポート
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit.py
    - 監査ログ用スキーマ定義 / 初期化
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・レート制御）
  - news_collector.py
    - RSS 収集・前処理・セキュリティ対策
- research/
  - __init__.py
  - factor_research.py
    - モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク関数

その他
- docs / design.md 等は含まれていませんが、各モジュール先頭の docstring に設計方針・処理フローを記載しています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API のパスワード（config に保管）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

---

## テスト・デバッグ時のヒント

- OpenAI / J-Quants の呼び出しは関数単位で _call_openai_api / _request 等をパッチできるよう設計されています（unittest.mock.patch を利用）。
- 自動 .env 読み込みを無効化し、テスト用の環境を明示的にセットアップしてください。
- DuckDB はメモリモード（":memory:"）での接続をサポートするため、ユニットテストでファイルを作らずに動作確認可能です。
- ニュース収集の外部通信はニュース収集モジュールの `_urlopen` をモックして切り替え可能です。

---

この README はライブラリ利用のための概要・導入・使い方をまとめたものです。各モジュールの詳細はソースコード先頭の docstring を参照してください。もし特定の使い方（例: kabuステーションとの連携、Slack 通知設定、監査ログのクエリ例）について詳細が必要であれば教えてください。
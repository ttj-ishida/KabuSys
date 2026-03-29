# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、ニュースのNLP評価（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを提供します。

---

## 主要機能（概要）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPXカレンダーの差分取得・保存（DuckDB）
  - 差分更新 / バックフィル / ページネーション対応、トークン自動リフレッシュ、レート制限対応
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（quality モジュール）
- ニュース収集・NLP
  - RSS からの記事収集（SSRF対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・銘柄別スコアリング（news_nlp）
- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュースのLLMセンチメントを組み合わせて日次レジーム判定（regime_detector）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン、IC計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal → order_request → executions の監査テーブル定義・初期化（冪等、UTCタイムスタンプ）

---

## 要求環境

- Python 3.10 以上（型アノテーションに | を使用）を推奨
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外を使うモジュールが増えた場合は適宜追加）

※プロジェクトに requirements.txt / pyproject.toml がある想定でインストールしてください。

---

## セットアップ手順

1. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存ライブラリのインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクト配布形式に合わせて:
   ```
   pip install -e .
   ```
   または
   ```
   pip install -r requirements.txt
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。
   - 必須の環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=... （news_nlp / regime_detector で使用。関数呼び出し時に引数で渡すことも可能）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下は最小限の利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続の作成（設定経由のパス利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # Path -> str
  ```

- 日次 ETL 実行（データ取得・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されていれば api_key を省略可能
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Scored {n} symbols")
  ```

- 市場レジーム判定（1321 MA200 + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログDBの初期化（監査用 DuckDB を別ファイルで作成）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # 監査用ファイルパスは settings.duckdb_path とは別にすることを推奨
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算の呼び出し例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注記:
- OpenAI 呼び出しを行う関数（news_nlp.score_news、regime_detector.score_regime）は api_key 引数でキーを渡すことができます。渡さない場合は環境変数 `OPENAI_API_KEY` を参照します。
- 各公開関数は docstring に引数、戻り値、例外ポリシーが記載されています。特に外部API呼び出しやDBトランザクションの挙動（冪等性・ロールバック）に注意してください。

---

## よくある操作例 / コマンド（運用）

- 日次バッチ（cron）で ETL を実行する一例（Python スクリプトを作成して実行）:
  - スクリプト: scripts/daily_etl.py（簡易）
    ```py
    #!/usr/bin/env python3
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())
    ```
  - cron 例:
    ```
    0 6 * * * /path/to/venv/bin/python /path/to/project/scripts/daily_etl.py >> /var/log/kabusys/etl.log 2>&1
    ```

---

## ディレクトリ構成（主要ファイル）

（骨格）
```
src/kabusys/
├── __init__.py
├── config.py                     # 環境変数/設定管理
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py               # ニュースNLPスコアリング（OpenAI）
│   └── regime_detector.py        # 市場レジーム判定（MA + マクロLLM）
├── data/
│   ├── __init__.py
│   ├── jquants_client.py         # J-Quants API client & DuckDB 保存
│   ├── pipeline.py               # ETL パイプライン
│   ├── etl.py                    # ETL result export
│   ├── quality.py                # データ品質チェック
│   ├── stats.py                  # 統計ユーティリティ
│   ├── news_collector.py         # RSS ニュース収集
│   ├── calendar_management.py    # 市場カレンダー管理
│   ├── audit.py                  # 監査ログスキーマ初期化
│   └── ...                       # 他ユーティリティ
├── research/
│   ├── __init__.py
│   ├── factor_research.py        # ファクター計算
│   └── feature_exploration.py    # 将来リターン・IC・統計サマリー
└── ...
```

---

## 注意点 / 設計上の留意事項

- ルックアヘッドバイアス対策が多く組み込まれています：
  - 日付比較に `datetime.today()` や `date.today()` を関数内部で直接参照しない設計（呼び出し側が対象日を渡す）。
  - データ取得やスコア計算で「target_date 未満」「半開区間」等の扱いを徹底。
- 外部API呼び出し失敗時はフェイルセーフ（スコアを 0 にフォールバック、処理を継続）する箇所があるため、ログを確認して異常を検知してください。
- DuckDB に対する `executemany` の空リスト挙動など、実行環境のバージョン差に注意して実装されています。
- RSS ニュース収集は SSRF や XML Bomb 対策（defusedxml、ホスト判定、サイズ上限）を組み込んでいますが、追加の運用ルール（信頼できるフィードのみ登録等）を推奨します。

---

## 開発・寄稿

- コードのスタイルはドキュメンテーションストリングと型ヒントを重視しています。PR ではユニットテストと docstring の更新をお願いします。
- 自動環境変数読み込みを無効化したいテストや CI 環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## サポート / 参照

- 各モジュールに詳細な docstring が記載されています。API の具体的な戻り値形式やエラーハンドリングはそちらを参照してください。
- 実運用での監視（Slack 通知やログ集約）は別途実装を検討してください（設定値：SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。

---

以上が本コードベースの README.md（日本語）です。必要であれば、README に含めるサンプルスクリプトや、より詳細な環境変数一覧（必須 / 任意の区別）、あるいは CI / デプロイ手順を追記します。どの追加情報が必要か教えてください。
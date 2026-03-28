# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ。  
ETL（J-Quants → DuckDB）/ ニュースNLP（OpenAI）/ 市場レジーム判定 / ファクター計算 / データ品質チェック / 監査ログなど、トレーディングシステム構築に必要な基盤機能群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL（J-Quants API）
  - 日次株価（OHLCV）、財務（四半期BS/PL）、上場銘柄情報、JPXカレンダー取得（ページネーション・レート制御・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次ETLパイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS 収集（SSRF対策・URL正規化・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア化（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- データ品質チェック
  - 欠損、重複、スパイク（異常値）、日付不整合チェック（run_all_checks）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（冪等、UTC保存）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定）・環境変数経由の設定

---

## 必要条件

- Python 3.9+
- 推奨ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （HTTP/URL操作のため標準ライブラリを使用）
- J-Quants / OpenAI / Slack 等の外部APIキー

（プロジェクトには requirements.txt があればそれを使用してください。なければ上記パッケージをインストールしてください。）

例:
```
pip install duckdb openai defusedxml
# または
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン、パッケージをインストール
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```

2. 環境変数 / .env を用意する  
   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   必須環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション（注文APIパスワード等）
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL は省略可能（デフォルト http://localhost:18080/kabusapi）

   # OpenAI（score_news / score_regime で使用）
   OPENAI_API_KEY=sk-...

   # Slack 通知（任意だがプロジェクトで要求される）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベースパス（デフォルト）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境（development|paper_trading|live）
   KABUSYS_ENV=development

   # ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   LOG_LEVEL=INFO
   ```

3. DBディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表例）

以下は簡単な Python からの呼び出し例です。実行前に env の設定と必要なパッケージを用意してください。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務データの差分更新 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付与（OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジームスコア計算（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DBの初期化（監査専用DBを作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 使用時）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します（テスト等で使用）

---

## 開発・テストのヒント

- .env のパースは柔軟な実装になっています。クォートやコメント、export KEY=val 形式に対応。
- テスト時は環境を汚さないため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- OpenAI 呼び出し、ネットワークやIDトークン発行などの外部コールはモックしやすいように内部関数を分離しています（unittest.mock.patch 等で差し替え可能）。
- DuckDB の executemany に空リストを渡せないバージョン対策など、互換性に留意した実装です。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースNLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — 市場カレンダー管理
    - news_collector.py            — RSS 収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore）
    - audit.py                     — 監査ログ定義・初期化
    - etl.py                       — ETL インターフェースの再エクスポート
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - ai, research, data の各モジュール群が主要な処理単位です。

---

## 注意事項

- 外部API（J-Quants, OpenAI, kabuステーション 等）にはレート制限や認証があるため、実運用ではキー管理、レート制御、エラーハンドリングの設定を適切に行ってください。
- 本ライブラリの一部機能は実際の注文（発注）処理に繋がる設計を含みます。live 環境での運用は十分なテストとリスク管理のもとで行ってください（KABUSYS_ENV=live）。
- 時刻・タイムゾーンは設計上 UTC / JST の扱いに注意している箇所があります。バックテスト等でルックアヘッドバイアスを防ぐ設計が組み込まれています。

---

必要に応じて README に追加したい内容（例: CLI コマンド、CI 設定、例データ、schema 初期化手順など）があれば教えてください。
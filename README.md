# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質検査、監査ログ（発注トレース）などの共通機能を提供します。

---

## 主要機能（ハイライト）

- データ ETL（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - ページネーション対応、レート制限・リトライ、トークン自動リフレッシュ
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip/サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存フロー想定
- ニュース NLP / AI スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント算出（JSON Mode）
  - エラーハンドリング、バッチ処理、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントを合成して日次で判定
  - LLM 呼び出し保護（リトライ、フェイルセーフ）
- Research ツール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC（Information Coefficient）算出、Z スコア正規化 等
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出と QualityIssue レポート
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査テーブル定義と初期化ユーティリティ
  - 発注フローのトレーサビリティを UUID 連鎖で保証

---

## セットアップ

前提:
- Python 3.10+（型注釈で `|` 型や typing の機能を使用）
- DuckDB、OpenAI Python SDK、defusedxml などが必要

1. リポジトリをクローンして editable install（例）:
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m pip install -e ".[all]"    # 実際の extras 名はプロジェクトの packaging に依存します
   ```
   ※ packaging が整備されていない場合は必要なライブラリを手動でインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```

2. 環境変数 / .env
   - ルート（.git や pyproject.toml のある場所）配下の `.env` および `.env.local` を自動で読み込みます（デフォルト）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで有用）。
   - 必須環境変数（少なくとも開発・実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector 等）を利用する場合
   - 任意 / デフォルト可能:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト data/monitoring.db）

   例 `.env`（.env.example を参考に作成してください）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は最小限の利用例です。適宜ロギング設定や例外処理を追加してください。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は今日が対象（calendar により営業日に調整）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- OpenAI を用いたニューススコアリング（銘柄別 ai_scores への書き込み）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作成）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例: momentum）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - 日付参照は基本的に明示的な target_date を用いるか、ETL の起点で調整する。内部で datetime.today() / date.today() を直接参照しない箇所が多い設計です。
- 冪等性:
  - ETL / 保存処理は ON CONFLICT DO UPDATE 等で冪等に作られており、繰り返し実行してもデータ破壊を抑制します。
- API 呼び出しの堅牢性:
  - J-Quants・OpenAI 呼び出しはリトライ・バックオフ・ステータスチェックを実装しており、致命的な失敗はログを残してフェイルセーフ（ゼロ値）で継続する箇所がある設計です。
- セキュリティ:
  - RSS のフェッチは SSRF 対策、最大受信サイズ制限、defusedxml を用いた XML パース等を実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys の主要モジュールとファイル（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 呼び出し、バッチ処理）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（認証・取得・保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - news_collector.py       — RSS 収集、前処理、保存ロジック
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - stats.py                — 汎用統計ユーティリティ（Zスコア等）
    - quality.py              — データ品質チェック（欠損・スパイク等）
    - audit.py                — 監査ログスキーマ / 初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — forward returns / IC / 統計サマリー

（上記はコードベースから抜粋した主要コンポーネントの一覧です）

---

## よくある運用タスク

- 定期 ETL（cron / scheduler）:
  - run_daily_etl を日次で起動してデータを更新
- ニュース収集:
  - news_collector.fetch_rss をソースごとに呼び出し、取得記事を raw_news / news_symbols に保存する ETL を作成
- モデル実行（戦略）:
  - research と data の出力を組み合わせてシグナル生成。生成したシグナルを監査テーブルに保存し、order_requests を経由して発注実行（発注層は別途実装）

---

## 開発 / テスト

- 環境変数自動ロードが邪魔な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- OpenAI 呼び出し／外部 API 呼び出しはモック可能な設計（モジュール内の _call_openai_api、_urlopen、jquants_client._request などを patch）です。ユニットテストではこれらを差し替えて実行してください。

---

## ライセンス / 貢献

- この README にはライセンス情報は含まれていません。リポジトリのトップレベルにある LICENSE を参照してください。  
- 貢献の際は issue/PR を経てください。コードスタイル・型注釈・ロギング方針に沿うことを推奨します。

---

以上が本リポジトリの概要と導入手順です。具体的な実行や運用に関して、さらにサンプルスクリプトや CI/CD の例を追加したい場合はお知らせください。
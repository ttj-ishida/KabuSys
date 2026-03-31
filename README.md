# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL、ニュース収集・NLP、ファクター計算、監査ログ、研究用ユーティリティなどを包括したモジュール群を提供します。

主な用途
- J-Quants API からのデータ取得（株価 / 財務 / 市場カレンダー）
- DuckDB ベースの ETL パイプラインと品質チェック
- RSS ニュース収集と OpenAI を用いたニュースセンチメントのスコアリング
- 市場レジーム判定（MA200 と マクロニュースの組合せ）
- ファクター計算・特徴量探索（研究用）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- 設定管理（環境変数 / .env 自動読込）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意: KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL, OPENAI_API_KEY 等
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付整合性）
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限管理、リトライ、トークン自動リフレッシュ
  - fetch / save の idempotent 実装（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出・ai_scores 書き込み
  - バッチ処理・リトライ・レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成してレジーム判定
- 研究用モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

---

## セットアップ手順

前提
- Python 3.9+（コード内 typing などを利用しています）
- ネットワークアクセス（J-Quants API / OpenAI / RSS 取得）

1. リポジトリをクローン / ソース配置
   - 既にパッケージが src/kabusys 下に配置されている前提です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要な主な依存例（環境に合わせて適宜追加してください）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```
   開発用に packaging / lint 等がある場合は requirements-dev を用意してください。

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数設定
   プロジェクトルートの .env または OS 環境に以下を設定してください（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - パッケージはプロジェクトルートに .env / .env.local があれば自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須 env が未設定だと Settings プロパティ呼び出し時に ValueError が発生します。

---

## 使い方（主要な例）

以下は簡易的な利用例です。実運用時はログ設定やエラーハンドリングを適切に行ってください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を利用しても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定済みであること
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} codes")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

注意点
- OpenAI 呼び出しは API レート・料金が発生します。API キーの管理と環境設定を行ってください。
- J-Quants API はレート制限（120 req/min）等があるため、jquants_client は内部で制御しますが、ID トークンやネットワーク状態に注意してください。
- ETL / AI モジュールは look-ahead bias を避ける設計がなされています（target_date 未満のみ参照等）。

---

## 重要な環境変数

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルトは development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO
- DUCKDB_PATH / SQLITE_PATH — DB のパスは Settings で default を持ちますが環境変数で上書き可
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化

---

## ディレクトリ構成（概要）

（src/kabusys 下の主要ファイル・モジュール）
- __init__.py — パッケージ定義（data, strategy, execution, monitoring をエクスポート）
- config.py — 環境設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（銘柄スコアリング）
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save、認証、レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマと初期化
  - news_collector.py — RSS 収集・正規化
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- その他: strategy, execution, monitoring パッケージ（このコードベースでは参照用に __all__ に含まれていますが、実装の状況により追加）

---

## 実運用上の注意・トラブルシューティング

- OpenAI: レスポンス形式を厳密に JSON で期待していますが、時折余計なテキストが混ざるためパースのリカバリ処理があります。API 制限やエラー時はフェイルセーフでスコア 0.0 を用いる設計です。
- J-Quants: 401 時のトークンリフレッシュ、自動リトライ、レート制御を実装しています。ID トークン取得には JQUANTS_REFRESH_TOKEN が必要です。
- DuckDB: executemany に空リストを渡せないバージョンを考慮した実装が含まれます。DB スキーマの初期化手順（audit.init_audit_schema 等）を利用してください。
- RSS: SSRF・gzip bomb 等の防御ロジックが組み込まれています。外部 RSS を追加する場合はソースの信頼性を確認してください。
- テスト時: 自動 .env 読み込みを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。AI 呼び出しやネットワーク呼び出しはモック化してテストすることを推奨します。

---

この README はコードベースの主要点をまとめたものです。詳細な API 使用法やスキーマ定義は各モジュールの docstring や関数のドキュメント（ソースコード内コメント）を参照してください。必要であればサンプル .env.example や初期スキーマ作成スクリプトのテンプレートも作成します。必要な追加情報を教えてください。
# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ（プロトタイプ）

このリポジトリは、J-Quants / JPX データを取得して DuckDB に保存する ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注／約定トレース）の初期化などのユーティリティ群を提供します。実際の発注（ブローカー連携）やフル運用の注文フローは別モジュール（execution 等）と連携する設計になっています。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local から自動読み込み（パッケージ配布後も cwd に依存しないルート探索）
  - 必須環境変数のバリデーション

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と保存
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）

- ニュース収集・NLP（kabusys.data.news_collector / kabusys.ai.news_nlp）
  - RSS フィードからの安全なニュース収集（SSRF/圧縮/サイズ制限対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（ai_scores への書き込み）
  - LLM 呼び出しのバッチ処理、JSON モードのレスポンス検証、堅牢なリトライ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321, 日経225連動）200日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して
    日次で 'bull' / 'neutral' / 'bear' を判定し market_regime テーブルへ保存

- 研究（kabusys.research）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化ユーティリティ
  - init_audit_db による DuckDB での監査 DB 初期化（UTC タイムゾーン固定）

---

## 要求環境 / 依存ライブラリ

- Python 3.10 以上（typing の新構文を利用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

例: 簡易 requirements.txt
- duckdb
- openai
- defusedxml

インストール例:
```bash
python -m pip install -r requirements.txt
# または
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（利用する機能により変動）
   - OpenAI を使う機能を実行する場合: OPENAI_API_KEY を設定
   - その他:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効にする場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB データベース用ディレクトリを準備（例: data/）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリの典型的な使い方です。すべて Python スクリプト/REPL で実行できます。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（market_regime へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルにアクセスできます
```

- 研究用関数の利用（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: J-Quants API を使う場合）
- OPENAI_API_KEY: OpenAI API キー（ニュース/NLP・レジーム判定に必要）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（注文機能使用時）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（動作モード）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を行う場合に必要
- DUCKDB_PATH, SQLITE_PATH: DB ファイルパスの上書き

注意: Settings は kabusys.config.settings として公開されています。アプリケーション内で settings.jquants_refresh_token などを利用できます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python パッケージ構成（src/kabusys）を抜粋しています。

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py          -- ニュースの NLP スコアリング（OpenAI）
      - regime_detector.py   -- 市場レジーム判定（ETF MA + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py    -- J-Quants API クライアント + DuckDB 保存
      - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
      - etl.py               -- ETL 公開インターフェース（ETLResult 再エクスポート）
      - news_collector.py    -- RSS ニュース収集・前処理
      - quality.py           -- データ品質チェック
      - stats.py             -- 汎用統計ユーティリティ（zscore_normalize等）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
      - audit.py             -- 監査ログテーブル定義・初期化
    - research/
      - __init__.py
      - factor_research.py   -- モメンタム/ボラティリティ/バリュー等
      - feature_exploration.py -- 将来リターン・IC・統計サマリー等
    - (その他) execution/, monitoring/ 等は __all__ に含まれますが本 README のコードベースでは一部未実装／省略の可能性があります

---

## 実行上の注意 / 設計上のポイント

- Look-ahead bias（未来情報参照）を防ぐ設計
  - 多くの関数は内側で date.today() 等を参照せず、target_date を明示的に受け取ります。
  - DB からの抽出は target_date より前のみを使う等の工夫があります。

- LLM 呼び出しは失敗してもフェイルセーフ
  - OpenAI API 呼び出しでエラーが起きた場合はスコアを 0 にフォールバックするなど、堅牢性を優先する動きがあります。

- ETL は idempotent（重複更新防止）
  - DuckDB への保存は ON CONFLICT を用いた上書きが基本になっています。

- セキュリティ / ネットワーク対策
  - RSS フェッチでは SSRF 防止、受信サイズ上限、gzip 解凍後の検査などの対策が組み込まれています。
  - J-Quants クライアントはレート制御とリトライを行い、401 発生時はトークン自動更新を試みます。

---

## よくある用途のワークフロー例

1. 毎晩 03:00 に run_daily_etl を実行してデータを更新
2. 朝のバッチで score_news を走らせ ai_scores を更新
3. score_regime を実行して当日の市場レジームを判定
4. リサーチ環境で factor を計算し、シグナル生成・監査ログに保存
5. 取引を実行する場合は execution モジュールを通じて order_requests を挿入・監査トレース

---

## テスト・開発時の便利なポイント

- 自動 .env ロードを無効化する（テスト内で環境を制御する場合）
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク I/O は関数単位でモック可能（コード内で _call_openai_api / _urlopen などを差し替える想定）
- DuckDB は ":memory:" を渡すことでインメモリ DB を利用可能（ユニットテストで便利）

---

この README はコードベースに含まれるモジュールの概要と典型的な使い方をまとめたものです。詳細な API ドキュメントや運用手順、CI/デプロイ設定は別途付随ドキュメント（DataPlatform.md / StrategyModel.md 等）に従ってください。必要であれば README を拡張してサンプルスクリプトや SQL スキーマ定義、より詳しい環境変数一覧を追加できます。
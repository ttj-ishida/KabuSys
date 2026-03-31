# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI を連携してデータ取得・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算などを行うモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（主な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株データの収集（J-Quants 等）、ニュース収集・NLP（OpenAI を用いたセンチメント）、データ品質チェック、ファクター計算、監査ログ（発注→約定トレーサビリティ）など、定量投資／自動売買の基盤的処理を行う Python パッケージです。設計上、バックテストにおけるルックアヘッドバイアスを避ける工夫や API 呼び出しの堅牢性（リトライ、レート制御）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（OS 環境変数が優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ取得 / ETL（kabusys.data.pipeline, jquants_client）
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得
  - 保存は idempotent（ON CONFLICT / upsert）で DuckDB に格納
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（急騰／急落）、重複、日付不整合の検出
  - QualityIssue 型で結果を返却

- ニュース収集（kabusys.data.news_collector）
  - RSS 収集・前処理・SSRF 防止、トラッキングパラメータ除去、記事ID のハッシュ化
  - raw_news / news_symbols への冪等保存を想定

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント生成（JSON Mode）
  - バッチ処理、リトライ、レスポンスバリデーション、ai_scores テーブルへ保存

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成し regime（bull/neutral/bear）判定

- リサーチユーティリティ（kabusys.research）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC 計算、統計サマリー、z-score 正規化

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB データベース初期化（UTC タイムゾーン固定）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `X | Y` を使用しているため）
- Git クローン済みのリポジトリ

1. 仮想環境を作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   代表的な依存：
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（OS 環境変数優先）。
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 簡単な使い方（コード例）

以下は主要なユースケースの最小例です。実行前に必要な環境変数（下記参照）を設定してください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を参照しても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を利用
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# テーブルが作成された conn を使って監査ログを書き始める
```

- 設定値の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

---

## 環境変数（主な設定）

必須（アプリ機能による）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 実行で必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector などで使用）
- KABU_API_PASSWORD : kabuステーション のパスワード（注文実行系を使う場合）
- SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID : 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB など用（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視系）

.env 自動ロードについて
- 実行時、プロジェクトルート（.git または pyproject.toml の親ディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。OS の環境変数が優先され、`.env.local` は既存キーの上書きを許可します。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成

主要ファイル／パッケージ（src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数読み込み・設定オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py              # マーケットレジーム判定（1321 MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py          # 市場カレンダー管理 / 営業日判定
    - etl.py                          # ETL の公開インターフェース（ETLResult 再エクスポート）
    - pipeline.py                     # 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py                        # z-score 正規化等の統計ユーティリティ
    - quality.py                      # データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                        # 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py               # J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py               # RSS 取得・前処理・SSRF 対策
  - research/
    - __init__.py
    - factor_research.py              # Momentum/Value/Volatility ファクター計算
    - feature_exploration.py          # forward returns / IC / summary / rank
  - その他：strategy / execution / monitoring 等のトップレベル公開（パッケージ __all__ に含む）

---

## 補足・運用上の注意

- Look-ahead バイアス防止
  - 多くのモジュールは内部で datetime.today() や date.today() を無条件に参照せず、関数呼び出し時に明示的に target_date を渡す設計です。バックテスト時は必ず過去データだけを使うよう注意してください。

- API コールの堅牢性
  - J-Quants / OpenAI 呼び出しにはリトライ・バックオフ・レート制御が組み込まれていますが、実運用時の API 制限やコストに注意してください。

- DuckDB スキーマ
  - モジュールは特定のテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_calendar, market_regime 等）を前提に動作します。初回は適切なスキーマ作成が必要です（ETL パイプライン・audit.init_audit_schema を利用して初期化してください）。

---

必要に応じて README に実行スクリプト例や CI / テストのセットアップ手順、詳細なスキーマ定義・SQL DDL を追加できます。追加で欲しいサンプルやセクションがあれば教えてください。
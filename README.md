# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集と NLP による銘柄センチメント評価・市場レジーム判定・監査ログ（トレーサビリティ）など、取引システムやリサーチ用途で必要な機能をまとめています。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（冪等）
  - ETL パイプライン（差分取得／バックフィル／品質チェック）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合などのチェックを実行して問題を収集
- カレンダー管理
  - JPX（祝日・半日・SQ）を保持し、営業日判定や前後営業日の取得を提供
- ニュース収集
  - RSS フィードからの取得、前処理、raw_news / news_symbols への保存（SSRF対策・サイズ制限・トラッキング除去）
- AI（OpenAI）連携
  - ニュースごとのセンチメント（銘柄ごと）を LLM で評価して ai_scores に保存
  - マクロニュース + ETF（1321）の MA200 乖離を合成して日次の市場レジーム（bull/neutral/bear）を判定
  - リトライやフェイルセーフ設計（API失敗時は中立扱い等）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化関数
  - UUID を用いた冪等キー・状態遷移管理
- 研究（Research）ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC・統計サマリー、Zスコア正規化

---

## 要求環境 / 依存関係

- Python >= 3.10（型アノテーションや union 型を利用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- （運用に応じて）J-Quants の認証情報、OpenAI API キー、kabu API のパスワード、Slack トークンなど

requirements.txt（例）
```
duckdb
openai
defusedxml
```

---

## 環境変数 / 設定

本パッケージは .env ファイルまたは環境変数から設定を自動読み込みします（プロジェクトルートに .git または pyproject.toml を検出して .env を読み込みます）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な設定キー（Settings で参照される環境変数）
- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY  
  - OpenAI API キー（AI 機能を使う際に必要）
- KABU_API_PASSWORD  
  - kabuステーション API のパスワード（発注系を使う場合）
- KABU_API_BASE_URL（任意）  
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  
  - Slack 通知を行う場合に必要
- DUCKDB_PATH（任意）  
  - デフォルト DB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）  
  - 監視用途の SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）  
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（任意）  
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

プロジェクトルートに .env.example を置き、そこから .env を作成してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   ※requirements.txt が無い場合は duckdb / openai / defusedxml を個別にインストールしてください。
4. 環境変数を設定
   - プロジェクトルートに `.env` を作り必要な変数を設定します（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=/path/to/data/kabusys.duckdb
     ```
5. DuckDB ファイルやディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト内でライブラリを呼び出す例です。MyPy / linters のために import path を調整してください。

1) DuckDB 接続と日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None は OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

3) 市場レジーム判定（market_regime テーブルに書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB を初期化する（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルとインデックスが作成されます
```

5) 設定値にアクセスする例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 環境変数が未設定だと ValueError を発生
print(settings.duckdb_path)
```

注意:
- AI の呼び出しは OpenAI の API キーが必要です（関数引数に api_key を渡すか環境変数 OPENAI_API_KEY をセット）。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を必要とします。

---

## 主要モジュール / ディレクトリ構成

（プロジェクトの主要なファイルと役割を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み（.env 自動ロード）と Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - news_collector.py
      - RSS ベースのニュース収集（SSRF 対策、前処理、raw_news 保存）
    - calendar_management.py
      - JPX カレンダー管理と営業日判定 / 更新ジョブ
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
    - etl.py
      - ETL 公開インターフェース（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリューなどの計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数
  - ai、research 等の補助モジュール群

---

## 運用上の注意 / 設計上のポイント

- Look-ahead bias の回避:
  - 多くの関数は内部で現在時刻を参照せず、明示的な target_date を受け取ります。
  - DB クエリは target_date 未満や <=/ < を適切に使い、未来情報を参照しないように設計されています。
- 冪等性:
  - J-Quants の保存処理は ON CONFLICT DO UPDATE を使い冪等に保存します。
  - 監査ログの order_request_id は冪等キーとして想定されています。
- フェイルセーフ:
  - OpenAI 呼び出しや API エラー時は極力例外を全体に波及させず、中立値で継続する設計が多く採用されています（ただし、必要であれば例外が上がる箇所もあります）。
- レート制御:
  - J-Quants はモジュール内でレート制限を行います（120 req/min を想定）。
- セキュリティ:
  - news_collector ではリダイレクト時の検証やプライベートアドレス検査、受信サイズ制限、defusedxml を利用した XML パース等、SSRF や DoS に対する防御が入っています。

---

## よく使う問い合わせ先（参考）

- ETL 実行（スケジューラから呼ぶ）：kabusys.data.pipeline.run_daily_etl
- ニューススコア付与（AI）：kabusys.ai.news_nlp.score_news
- 市場レジーム判定（AI）：kabusys.ai.regime_detector.score_regime
- 監査 DB 初期化：kabusys.data.audit.init_audit_db / init_audit_schema

---

以上です。README の内容を運用環境や CI/CD 用に合わせて調整してください（例: systemd / cron / Airflow に合わせたランナー、ログ設定、Secrets 管理の具体化など）。必要であれば実行例スクリプトや Dockerfile、Makefile 例も作成しますのでお申し付けください。
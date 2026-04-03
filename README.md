# KabuSys

日本株向け自動売買 / データパイプライン ライブラリ。  
J-Quants からのデータ取得、DuckDB への保存、ニュースの NLP スコアリング、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は日本株のデータプラットフォーム・リサーチ・アルゴリズムトレード基盤のためのモジュール群です。主に以下の領域をカバーします。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と前処理（SSRF 対策・サイズ制限などを考慮）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／市場レジーム判定
- DuckDB を中心とした保存・監査スキーマ
- ファクター計算・特徴量探索・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、バックテストでのルックアヘッドバイアス防止（target_date を明示して過去データのみ参照）や、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS からニュース収集、前処理、raw_news への保存支援
  - calendar_management: JPX カレンダー管理・営業日判定・バッチ更新
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
  - stats: 汎用統計・Zスコア正規化
- ai/
  - news_nlp.score_news: 銘柄毎にニュースをまとめて OpenAI でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- research/
  - factor_research: momentum / value / volatility 等の定量ファクター計算
  - feature_exploration: 将来リターン算出、IC 計算、統計サマリー
- config:
  - 環境変数読み込みと Settings（.env 自動読み込み、重要設定の取得）

---

## 前提・依存

- Python 3.10 以上（構文で | 型ヒント等を使用）
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- J-Quants / OpenAI の API キー

requirements.txt がプロジェクトにある場合はそちらを使用してください。手動でインストールする場合の例:

pip install duckdb openai defusedxml

（実環境ではバージョン固定・仮想環境での利用を推奨）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージをインストール）
   - 開発環境で編集する場合:
     pip install -e .

2. 必要な環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（環境変数が優先）。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   推奨される（主要な）環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # LINE 通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（これらを要求する機能を利用する場合）
   - OpenAI を使う機能を使う場合は OPENAI_API_KEY を設定してください（関数呼び出しで引数として渡すことも可能）。

3. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は Python REPL / スクリプトでの利用例です。

- settings の取得:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（target_date を指定することでルックアヘッド防止）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを引数で与えることも可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用DBを作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って order_requests 等を操作
```

- ファクター計算（例: モメンタム）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{'date': ..., 'code': 'xxxx', 'mom_1m': ..., ...}, ...]
```

注意:
- OpenAI を呼ぶ関数は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定します。
- テスト時には内部の OpenAI 呼び出し関数をモックできるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api のパッチ等）。

---

## 設定の自動ロードについて

- config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成

主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの NLP スコアリング
    - regime_detector.py     # 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン
    - news_collector.py     # RSS 収集・パース
    - calendar_management.py# 市場カレンダー管理
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（zscore 等）
    - audit.py              # 監査ログスキーマ初期化
    - etl.py                # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # Momentum/Value/Volatility 等
    - feature_exploration.py# forward returns, IC, summaries
  - ai/ (上記)
  - research/ (上記)

（上記はコードベースの主要モジュールを示しています。プロジェクトには追加のユーティリティや補助モジュールが含まれる場合があります。）

---

## 開発・テスト向けノート

- OpenAI や J-Quants の API 呼び出しは外部依存のため、ユニットテストでは該当関数をモックしてください。
  - news_nlp / regime_detector 内部で呼ばれる _call_openai_api は patch して差し替え可能です。
  - jquants_client._request やネットワーク関連も同様にモック可能です。
- 自動 .env 読み込みをテストで制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を用いるため、インメモリ ":memory:" 接続で単体テストを実行できます。

---

## 既知の環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants トークン)
- KABU_API_PASSWORD (必須: kabu API パスワード)
- OPENAI_API_KEY (OpenAI 利用時必須)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- DUCKDB_PATH / SQLITE_PATH (データベースファイルパス)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視関連）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

設定は kabusys.config.settings 経由で取得できます。

---

## ライセンス・貢献

（本リポジトリのライセンス情報をここに記載してください。貢献方法・PR ポリシー等があれば追記してください。）

---

README は以上です。必要であれば、セットアップ用の requirements.txt、.env.example、または使用例のスクリプト（ETL 実行/監査初期化など）を追記できます。どの部分を具体的に補足したいか教えてください。
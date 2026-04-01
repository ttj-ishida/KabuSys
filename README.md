# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援モジュール群（自動売買システムの基盤ライブラリ）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株のデータ収集（J-Quants / RSS）、データ品質チェック、特徴量計算（ファクター）、LLM を使ったニュース感情分析や市場レジーム判定、そして監査ログ（order/signal/execution）スキーマ初期化など、自動売買／リサーチの基盤となるユーティリティをまとめた Python パッケージです。DuckDB を主要なローカルデータストアとして使用します。

設計方針の要点：
- ルックアヘッドバイアスを避ける設計（日時処理で現時点参照を最小化）
- ETL / 品質チェックは Fail-Fast にせず問題を全件収集
- 外部API（J-Quants, OpenAI）呼び出しはリトライやレート制御・フェイルセーフを実装
- 冪等性（DB書き込みは ON CONFLICT / DELETE→INSERT による置換）を重視

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード、必須/任意設定のラッパ）
- J-Quants API クライアント（株価・財務・市場カレンダー取得、保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS → raw_news, news_symbols への保存、SSRF対策など）
- LLM を用いたニュースセンチメント分析（gpt-4o-mini, JSON mode）
- 市場レジーム判定（ETF 1321 の MA と LLM センチメントの合成）
- 研究用ユーティリティ（モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）および専用 DB 初期化関数
- Slack 等への通知用の設定項目（Slack トークン・チャンネルID を管理）

---

## 前提条件

- Python 3.10+
- DuckDB
- OpenAI Python SDK（gpt 系を呼ぶため）
- defusedxml（RSS パースの安全化）
- （利用する機能に応じてネットワークアクセス権限、J-Quants/OpenAI の API キー）

推奨パッケージ（最低限）:
- duckdb
- openai
- defusedxml

（実際の requirements.txt はリポジトリに応じて用意してください）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - pip install duckdb openai defusedxml
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動でロードされます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 必要であれば監査用 DB を初期化
   - 以下の例を参照して DuckDB ファイルを作成・初期化します。

---

## 主要な環境変数

（必須は明示）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に用いる）
- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード（使う機能がある場合）
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須, Slack通報を使う場合)
- SLACK_CHANNEL_ID (必須, Slack通報を使う場合)
- OPENAI_API_KEY (必須, AI 機能を使う場合)
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PID_FILE_PATH
  - デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視の閾値（%）
- KABUSYS_ENV
  - 有効値: development / paper_trading / live
  - デフォルト: development
- LOG_LEVEL
  - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

---

## 使い方（コード例）

※ 以降の例では DuckDB 接続に `duckdb` モジュールを使っています。

- 設定の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作って ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア算出（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 を基準に MA とマクロニュースを統合）
```python
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- 監査用 DB の初期化（独立した監査 DB を作成する例）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使って order/signal/execution を記録できます
```

---

## 開発・テストのヒント

- OpenAI / 外部 API 呼び出しはユニットテスト時にモックすることを推奨します。
  - モジュール内の `_call_openai_api` を patch する設計になっています。
- .env 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境向け）。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード側で空チェックを行っています。テストでも同様に考慮してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 data 関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ公開一覧に含まれているが詳細は実装次第)

README は実装と同期して更新してください。実際に運用する際は API キーと DB のバックアップ・アクセス制御を十分に行ってください。

---

以上。必要があれば「README に追加したい利用例」や「.env.example のサンプル」を作成します。どの形式が良いか教えてください。
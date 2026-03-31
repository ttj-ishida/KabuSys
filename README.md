# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
ETL（J-Quants からのデータ取得）・ニュースセンチメント解析（OpenAI）・市場レジーム判定・研究用ファクター計算・監査ログなど、取引システムのバックエンドに必要な機能群を提供します。

主な設計方針として、以下を重視しています。
- Look-ahead bias を避ける（内部で現在日時を勝手に参照しない設計）
- DuckDB を利用したローカルデータレイヤ
- 外部 API 呼び出しはリトライやレート制御を備える
- 冪等性（ON CONFLICT / idempotent な保存）
- セキュリティ配慮（RSS の SSRF 対策、defusedxml など）

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）／必須環境変数の取得
- データ取得（J-Quants API）
  - 株価日足（OHLCV）取得、保存（差分取得・ページネーション対応）
  - 財務データの取得・保存
  - JPX マーケットカレンダー取得・保存
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 個別ジョブ（prices / financials / calendar）の実行ユーティリティ
  - ETL 実行結果を表す ETLResult
- データ品質チェック
  - 欠損、重複、将来日付、価格スパイクなどの検出（QualityIssue で返却）
- ニュース収集／NLP（ニュースセンチメント）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI を使った銘柄ごとのニュースセンチメント（JSON mode 対応、バッチ処理）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定
- 研究用モジュール
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン、IC（Spearman）計算、統計サマリー、Z スコア正規化
- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions 等の DDL と初期化ユーティリティ
  - 監査用 DuckDB の初期化関数（UTC タイムゾーン固定）
- AI 周り、HTTP クライアント、レートリミッタ、エラーハンドリングなどのユーティリティ

---

## 動作環境 / 依存

- Python >= 3.10（型アノテーションで | を使用）
- 推奨パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで実装された部分もありますが、OpenAI や DuckDB 周りは外部パッケージが必要です。

インストール例（仮）:
```
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 開発中でソースを編集する場合
python -m pip install -e .
```

※ pyproject.toml / requirements.txt がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くことを想定）
   - 自動ロード: パッケージ起動時に .env / .env.local が自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB 用データディレクトリ / ファイルの準備（既定: data/kabusys.duckdb）

推奨（例）.env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu-station（注文 API パスワード等）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack (通知などを使う場合)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# ローカルパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# システム設定
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数が未設定の場合は、Settings プロパティが ValueError を投げるので注意してください。

---

## 使い方（クイックスタート）

以下は Python スクリプト／REPL から利用する例です。各例では DuckDB 接続を渡して処理を実行します。

- DuckDB 接続を作る（デフォルトのファイルは settings.duckdb_path）
```python
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # 例: data/kabusys.duckdb
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行する（calendar → prices → financials → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が設定されているか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定を実行する（ma200 + macro sentiment を合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用関数の呼び出し例（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

---

## 注意点 / 運用メモ

- OpenAI 呼び出しや J-Quants API 呼び出しはレート制御・リトライを備えていますが、API キーや利用制限はユーザー側で管理してください。
- ETL / AI モジュールは Look-ahead bias を避ける設計になっています。target_date を明示して実行してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行います。CI などで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany に関する制約（空リスト不可）に配慮した実装になっています。
- RSS フィード収集は SSRF 対策やレスポンスサイズ上限を実装しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境設定読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースの LLM スコアリング
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存処理
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- 市場カレンダー管理・営業日ロジック
    - news_collector.py             -- RSS 収集
    - quality.py                    -- データ品質チェック
    - stats.py                      -- zscore_normalize 等の統計ユーティリティ
    - etl.py                        -- ETLResult の再公開
    - audit.py                      -- 監査ログ DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            -- momentum/volatility/value 計算
    - feature_exploration.py        -- forward returns / IC / summary
  - ai、data、research の他に strategy / execution / monitoring 等の名前は __init__ で公開される設計（個別実装ファイルはプロジェクト内を参照してください）

---

## よくある問題と対処

- 環境変数が足りない
  - Settings の各プロパティは未設定だと ValueError を投げます。README の「セットアップ手順」を参考に .env を用意してください。
- OpenAI / J-Quants の API 呼び出しが失敗する
  - ネットワークやキーに問題がある可能性があります。ログを確認し、必要に応じてリトライやキーの再生成を行ってください。J-Quants は 120 req/min のレート制限があるため、過負荷にならないよう注意してください。
- DuckDB にテーブルがない（テーブル存在前提の関数を呼んだ）
  - ETL pipeline や schema 初期化（監査用）は初回にテーブル作成を行うユーティリティがあるので、それらを利用してください（audit.init_audit_db など）。

---

必要があれば、README に以下の追加情報も追記できます：
- pyproject.toml / requirements の推奨セット
- CI / デプロイ手順（K8s / systemd の例）
- 実運用時の監視・アラート設定例（Slack 通知フロー）
- strategy / execution（売買アルゴリズム・約定処理）に関するドキュメント

ほかに README に入れたい具体的な内容（例: 実行スクリプト、Dockerfile、サンプル .env.example）や、英語版の追加が必要であれば教えてください。
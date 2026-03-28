# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を利用した銘柄センチメント）、市場レジーム判定、監査ログ（オーダー/約定のトレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止を重視（内部で date.today() 等に依存しない設計）
- DuckDB を中心としたローカルデータストア
- API 呼び出しにはリトライ / レート制御 / フェイルセーフを組み込み
- 各保存処理は冪等（idempotent）に設計

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価（日足）、財務、上場銘柄情報、JPX 市場カレンダー取得（ページネーション対応・レート制御・401 自動リフレッシュ）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク（急騰急落）、日付不整合（将来日付・非営業日データ）検出
- ニュース収集・前処理
  - RSS からのニュース取得（SSRF・Gzip・サイズ制限等の安全対策）、URL 正規化、記事ID 生成
- ニュース NLP（OpenAI）
  - 銘柄別センチメントスコア算出（gpt-4o-mini を JSON mode で使用）
  - 市場マクロセンチメント + ETF（1321）200日移動平均乖離を合成した市場レジーム判定
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化
  - 監査 DB の初期化ユーティリティ（UTC タイムゾーン強制、トランザクション選択可）
- 設定管理
  - .env（プロジェクトルートの `.env` / `.env.local`）自動ロード（無効化オプションあり）
  - 必須設定の抽出とバリデーション

---

## 要件（例）

- Python 3.10+
- DuckDB
- openai（OpenAI の Python SDK）
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

最低限インストール例（プロジェクトに requirements.txt がない場合の例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（実運用ではパッケージ固定の requirements.txt / Poetry / PEP 621 等で管理してください）

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成・有効化します。
2. 必要なパッケージをインストールします（上記参照）。
3. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可）。

推奨する .env の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu API
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL が必要なら上書き可能:
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI / News NLP
OPENAI_API_KEY=sk-...

# Slack 通知（必要時）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境とログレベル
KABUSYS_ENV=development       # development | paper_trading | live
LOG_LEVEL=INFO
```

環境変数の読み込みロジック：
- OS 環境変数 > `.env` > `.env.local` の順でロードされます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的な例）

以下はライブラリの代表的な呼び出し例です。実行前に必ず必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY など）を設定してください。

- DuckDB 接続の作成（設定からパス取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しないと今日が使われる
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の ma200 乖離 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査用テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

注意点：
- OpenAI の呼び出しはリトライ等の保護はあるものの API 利用料が発生します。テストでは api_key をモック化してください。
- AI 関連の関数は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの DB 書き込みは冪等に設計されています（ON CONFLICT 等）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- SLACK_BOT_TOKEN: Slack 用ボットトークン（通知機能）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知送信先）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に 1 を設定

---

## ディレクトリ構成（主要ファイル）

（パッケージルートが src/ のレイアウトを想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュース NLP（銘柄センチメント）
    - regime_detector.py  # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント・保存処理
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - etl.py              # ETL 結果クラスの再エクスポート
    - news_collector.py   # RSS ニュース収集
    - calendar_management.py  # 市場カレンダー管理・営業日判定
    - quality.py          # データ品質チェック
    - stats.py            # 基本統計ユーティリティ（zscore_normalize 等）
    - audit.py            # 監査ログ（DDL / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (上記)
  - research/ (上記)
  - その他: strategy / execution / monitoring 等のトップレベルサブパッケージが __all__ に準備されています（実装に応じて参照してください）

---

## 設計上の注意・運用メモ

- ルックアヘッドバイアス防止のため、各モジュールは target_date を明示的に受け取る設計です。バックテストや再現性の確保のため、date を固定して呼び出してください。
- ETL / 保存処理は冪等に設計されていますが、DB スキーマや外部依存が変わると挙動が変わる可能性があります。スキーマ変更時は注意してください。
- OpenAI 呼び出しはレスポンスの JSON バリデーションを行いますが、想定外のレスポンスが来た場合はフェイルセーフとしてスコア 0.0 やスキップで継続します。テストでは API 呼び出し部分をモックしてください。
- news_collector は SSRF / XML Bomb / 大容量攻撃対策を組み込んでいますが、外部 RSS の扱いは慎重に行ってください。

---

この README はプロジェクトの主要な利用シーンと構成をまとめたものです。実運用や開発を進める際は、各モジュールのドキュメント（docstring）を参照し、環境に応じた設定とテストを行ってください。
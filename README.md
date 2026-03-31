# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ（KabuSys）。  
DuckDB をデータレイヤに、J-Quants API やニュースフィード、OpenAI を利用した AI 補助機能を備えた ETL・リサーチ・監査基盤を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要環境と依存ライブラリ
- セットアップ手順
- 環境変数と設定 (.env)
- 使い方（簡易例）
  - 日次 ETL 実行
  - ニュースの NLP スコアリング
  - 市場レジーム判定
  - 監査 DB の初期化
  - 研究用ユーティリティ
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要
KabuSys は日本株のデータ収集（J-Quants/API、RSS ニュース）、品質チェック、AI を使ったニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）などを統合的に扱うライブラリ群です。バックテストや自動売買システムの基盤として利用できるよう設計されています。

設計方針のポイント：
- Look-ahead bias を避ける（内部で現在時刻を無闇に参照しない実装）
- DuckDB を中核にした ETL / 分析処理
- API 呼び出しはリトライとレート制御を実装
- 冪等性を考慮した保存処理（ON CONFLICT / idempotent）
- 監査ログでシグナル→発注→約定までトレース可能

---

## 機能一覧
主な機能（モジュール別）
- kabusys.config: 環境変数/.env の自動読み込み、設定取得
- kabusys.data
  - jquants_client: J-Quants API の取得・保存（株価、財務、カレンダー、上場情報）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）、個別 ETL ヘルパー
  - news_collector: RSS フィード取得と raw_news 保存（SSRF 対策・サイズ制限・トラッキング除去）
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: 汎用統計（Zスコア正規化 等）
- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に問い合わせ、銘柄ごとの ai_score を保存
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とマクロニュース LLM 評価を合成して市場レジーム判定
- kabusys.research: ファクター計算（momentum/value/volatility）、特徴量解析（forward returns, IC, summary）

---

## 必要環境と依存ライブラリ
- Python 3.9+（型ヒントで union 型等を使用）
- DuckDB
- OpenAI Python SDK（OpenAI API 呼び出し）
- defusedxml（RSS パースの安全化）
- そのほか標準ライブラリ（urllib, json, logging, datetime 等）

例（最低限の pip インストール）:
pip install duckdb openai defusedxml

（実際の requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール
   pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データファイル作成（必要に応じて）
   デフォルトでは data/kabusys.duckdb を使用します（settings.duckdb_path）。

---

## 環境変数（主な必須項目）
以下は Settings クラスで必須／デフォルト値が設定されているものです。未設定の場合はアクセス時に ValueError を送出します。

必須:
- JQUANTS_REFRESH_TOKEN   （J-Quants リフレッシュトークン）
- KABU_API_PASSWORD       （kabuステーション API パスワード）
- SLACK_BOT_TOKEN         （Slack 通知用 Bot トークン）
- SLACK_CHANNEL_ID        （通知先 Slack チャンネル ID）

OpenAI 関連:
- OPENAI_API_KEY          （news_nlp / regime_detector の呼び出しで利用）

オプション（デフォルトあり）:
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH            : data/kabusys.duckdb（default）
- SQLITE_PATH            : data/monitoring.db（default）
- KABU_API_BASE_URL      : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...

---

## 使い方（簡易例）
下記は Python REPL またはスクリプトからの呼び出し例です。各関数は duckdb 接続オブジェクト（duckdb.connect() の戻り値）を引数に受け取ります。

1) 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI を用いる）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を省略すると環境変数 OPENAI_API_KEY が使われます
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} symbols")
```

3) 市場レジーム判定（1321 の MA200 とマクロニュースを用いる）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査 DB 初期化（監査用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) 研究用ファクター計算の利用例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 詳細説明（ポイント）
- .env 自動ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を検出すると、.env と .env.local を自動で読み込みます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に有用）。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き可能）

- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini を利用する前提で JSON mode を使って厳密な JSON を期待します。
  - API 呼出しはリトライとバックオフを行い、致命的な障害でもシステム全体を停止させないフェイルセーフ設計（失敗時はスコア 0 等で続行）です。

- J-Quants クライアント:
  - レート制御（120 req/min）とリトライ、401 時のトークン自動リフレッシュを実装しています。
  - 保存は DuckDB に対して冪等（ON CONFLICT DO UPDATE）で行われます。

- ニュース収集:
  - RSS の取得は SSRF、防止（プライベート IP 判定、リダイレクト検査）、サイズ制限、XML のセーフパーサ（defusedxml）を使用して安全性を高めています。

---

## ディレクトリ構成（抜粋）
以下は本リポジトリ内の主要なモジュール構成です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - other modules for execution/strategy/monitoring (パッケージ公開名のみ __all__ に記載)

（実際のファイルツリーはリポジトリに依存します。ここには主要実装ファイルを抜粋しています。）

---

## 注意事項
- 本ライブラリには直接の発注実装（ブローカーへ送信する実装）は含まれない箇所があります。kabuステーション API を使った実行層は別モジュールで管理してください（パッケージでは execution 等の名前空間が公開されています）。
- OpenAI / J-Quants など外部 API 呼び出しのため、API キーやネットワークの取り扱いには注意してください（課金・レート制限）。
- 本パッケージはバックテストにおける look-ahead bias を避ける工夫を随所に施しています。内部で現在日時を不用意に参照していないか設計上の注意を払っていますが、バックテスト用途で使用する場合はデータ取得タイミングに注意してください。
- DuckDB に対する executemany の空リストバインドなど、バージョン依存の注意点が実装内にあります。実行環境の DuckDB バージョンに応じた検証を推奨します。

---

何か追加のドキュメント（API リファレンス、.env.example の自動生成、具体的な運用手順、テスト方法など）を作成する必要があればお知らせください。
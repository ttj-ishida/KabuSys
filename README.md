# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー収集）、ニュース収集・NLP、AI を使ったニュースセンチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株の量的運用パイプラインを構成するためのモジュール群です。主に以下を目的としています。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と前処理
- OpenAI を利用したニュースセンチメント（銘柄別・マクロ）と市場レジーム判定
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注から約定までの監査ログ用スキーマ（DuckDB への初期化・運用）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を参照しない設計が多く採用されています）
- 冪等性（ETL / 保存処理は ON CONFLICT / upsert 相当で安全）
- フェイルセーフ：外部 API 失敗時はスキップやデフォルト値で継続する実装が多い
- DuckDB を中心に軽量 DB を使用

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レート制御、リトライ）
  - market_calendar 管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS -> raw_news、SSRF 対策、トラッキング除去、前処理）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（銘柄別 ai_score を ai_scores テーブルへ）
  - マーケットレジーム判定（ETF 1321 の 200日 MA とマクロニュースの LLM センチメントを合成）
  - OpenAI 呼び出しは gpt-4o-mini を想定（JSON mode を利用）
- research
  - ファクター生成（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み（.env / .env.local を自動ロード、プロジェクトルート判定）
  - settings オブジェクト経由の設定アクセス（JQUANTS_REFRESH_TOKEN 等）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上を推奨（typing の | 型等を使用）
- システムに duckdb 等のバイナリ依存がある場合は OS 側の要件を満たすこと

1. リポジトリをクローンします（src/kabusys レイアウトを前提）。
2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（例）:
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e .  ※ pyproject.toml があれば編集のうえ実行
   - その他、ネットワークや DB 連携で必要なライブラリを追加してください。
4. 環境変数 / .env を準備します（以下参照）。

環境変数（必須・代表例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD : kabuステーション等の API パスワード（発注など）
- SLACK_BOT_TOKEN : Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID
- OPENAI_API_KEY : OpenAI 呼び出しに使用（ai モジュールで必須）
- KABUSYS_ENV : development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動 .env ロード：
- パッケージはプロジェクトルート（.git または pyproject.toml のある親）から .env と .env.local を自動で読み込みます
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

## 使い方（簡易ガイド）

以下は代表的な操作のサンプルです。実行前に必ず環境変数や DB パスを設定してください。

1) DuckDB 接続を作成（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しない場合は今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP（銘柄別センチメント）を実行
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI キーを引数で渡すか環境変数 OPENAI_API_KEY を用いる
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", count)
```

4) 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DB 初期化（監査専用 DB or 同じ DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn にスキーマ追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

6) ファクター計算（研究）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

ログレベルや挙動の調整は環境変数（LOG_LEVEL, KABUSYS_ENV 等）で行えます。

注意点：
- OpenAI への呼び出しは API キーが必要です。AI 周りの関数は api_key 引数で注入可能（テスト容易性のため）。
- ETL / news/ai の各処理は外部 API を呼びます。API レートやコストに注意してください。

---

## ディレクトリ構成（主なファイル / モジュール）

以下は本リポジトリの主要なモジュール構成（src/kabusys 配下）です。実装ファイルと機能の概略を示します。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                 — 銘柄別ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（ETF 1321 MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py      — 市場カレンダー（営業日判定 / 更新ジョブ）
    - etl.py                      — ETL 公開インターフェース（ETLResult）
    - pipeline.py                 — ETL パイプライン本体（run_daily_etl 等）
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - quality.py                  — データ品質チェック（QualityIssue）
    - audit.py                    — 監査ログスキーマ（DDL / init）
    - jquants_client.py           — J-Quants API クライアント（fetch/save etc.）
    - news_collector.py           — RSS ニュース収集・前処理
    - etl.py                      — ETL リザルトクラス（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 特徴量分析ユーティリティ（forward returns / IC / summary）
  - research/（その他モジュール）
  - ...（将来的に strategy / execution / monitoring などを含む名前空間が想定されています）

---

## 注意事項 / 運用上のヒント

- DuckDB のファイルはデフォルトで data/kabusys.duckdb に格納されます。パスは環境変数 DUCKDB_PATH で変更可能です。
- テスト・CI で .env 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や J-Quants API 呼び出しはコストとレート制限があるため、運用環境では適切なバックオフやバッチ化を行ってください（本コードでもリトライやレート制御を実装済み）。
- 監査ログ（audit）スキーマは一度作成したら基本的に削除せず運用する設計です。init_audit_schema の transactional フラグを適宜使ってください。
- ニュース収集は SSRF 対策やサイズ制限、XML パースの安全化（defusedxml）を行っています。外部ソースの取り扱いには注意してください。

---

## ライセンス / 貢献

本 README に含まれるライセンス表記や貢献ルールが別途提供されている場合はそちらに従ってください。コードベースへのパッチ提案や Issue はリポジトリの管理方針に従ってください。

---

必要であれば README の例（.env.example）、実運用ガイド（監視/アラート、バックアップ、テスト戦略）、デプロイ手順（systemd / cron / Airflow などでの ETL スケジューリング）を追加で作成します。どのドキュメントが欲しいか教えてください。
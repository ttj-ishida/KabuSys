# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を使用したセンチメント）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（主要 API の例）
- ディレクトリ構成
- 運用上の注意

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システム基盤ライブラリです。  
主に次の責務を持ちます：
- データプラットフォーム（J-Quants API からの差分 ETL、品質チェック）
- ニュース収集 / 前処理（RSS）と AI によるニュースセンチメントスコアリング
- 市場レジーム判定（ETF の移動平均乖離とニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、正規化等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env / 環境変数の読み込み）

設計にあたっては「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」等が意識されています。

---

## 機能一覧
- ETL: 日次 ETL（prices / financials / market_calendar）の差分取得・保存（DuckDB）
- 品質チェック: 欠損・重複・スパイク・日付不整合検出
- News Collector: RSS 取得・前処理・raw_news への保存（SSRF 対策やサイズ制限あり）
- News NLP: OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント（ai_scores への保存）
- Regime Detector: ETF(1321)の MA200 乖離 + マクロニュースセンチメントで日次市場レジーム判定
- Research: momentum / value / volatility のファクター計算、forward returns、IC、統計サマリー、z-score 正規化
- Audit: 監査テーブルの初期化・監査 DB の作成（signal_events / order_requests / executions）
- J-Quants クライアント: レート制御・リトライ・認証・ページネーション対応のデータ取得・保存関数

---

## 必要条件
- Python 3.9+（typing の表記や機能を利用）
- 主要依存パッケージ（参考）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt や pyproject.toml に合わせてインストールしてください）

例（仮）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - あるいは個別に: pip install duckdb openai defusedxml
4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある親ディレクトリ）に `.env` を置くと自動で読み込まれます（ただしテスト等で無効化可能）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 初期化（監査 DB 等）
   - 監査 DB を作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 環境変数（.env の例と注意点）

主な必須 / 推奨環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で必要）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（注文連携時）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env のパースは以下の点に対応しています：
- コメント行（#）の扱い、export KEY=VALUE フォーマット対応
- シングルクォート/ダブルクォート内でのエスケープ処理
- 自動ロード順序: OS 環境 > .env.local > .env

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API の例）

以下は基本的な Python からの呼び出し例です。DuckDB 接続を渡して各機能を呼び出します。

- DuckDB 接続の生成例：
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL（calendar / prices / financials の差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア算出（前日 15:00 JST ～ 当日 08:30 JST の記事を対象）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB の初期化（監査専用 DB ファイルを作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセス
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

- z-score 正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py           -- 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py       -- 市場カレンダー管理
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETL の公開型再エクスポート
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - quality.py                   -- 品質チェック（欠損・重複・スパイク等）
    - audit.py                     -- 監査ログテーブルの DDL / 初期化
    - jquants_client.py            -- J-Quants API クライアント（取得 / 保存）
    - news_collector.py            -- RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py           -- momentum / value / volatility 等
    - feature_exploration.py       -- forward returns / calc_ic / factor_summary / rank

---

## 運用上の注意
- OpenAI / J-Quants 等外部 API 呼び出しにはレート制限や料金が伴います。API キー・トークンは厳重に管理してください。
- news_nlp / regime_detector は OpenAI 呼び出しの失敗時にフェイルセーフとして 0.0 を返す設計ですが、API の制限やレスポンス形式変更には注意が必要です。
- DuckDB の一部操作（executemany 等）でバージョン依存の挙動があるため、プロジェクトで使用する duckdb のバージョンを合わせてください。
- 設定自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監査ログは削除前提ではなくトレーサビリティを保持する設計です。運用で DB サイズやバックアップ方針を検討してください。

---

この README はコードベースの主要機能と利用方法の概要をまとめたものです。各モジュールの詳細な使い方・引数仕様はソースコードの docstring を参照してください。必要であれば README にサンプルコマンドや CI/デプロイ手順を追記します。
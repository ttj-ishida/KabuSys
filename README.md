# KabuSys

KabuSys は日本株向けのデータプラットフォームと研究／自動売買基盤のライブラリ群です。J-Quants や RSS / OpenAI と連携してデータ収集（ETL）、データ品質チェック、ニュース NLP、マーケットレジーム判定、因子計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得・ETL
  - J-Quants API から株価（日足）・財務情報・マーケットカレンダーを差分取得・保存
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（差分取得 / バックフィル / 品質チェック）
- データ品質管理
  - 欠損、スパイク（急騰・急落）、重複、将来日付・非営業日の検出
  - QualityIssue 型で問題を収集
- ニュース収集・NLP
  - RSS から記事を収集して raw_news に格納（URL 正規化・SSRF 対策・サイズ制限）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（ai_scores へ保存）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- リサーチ機能
  - モメンタム・バリュー・ボラティリティ等の因子計算
  - 将来リターン計算、IC（スピアマンランク相関）、ファクター統計要約
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルでシグナル→発注→約定のフローを追跡
  - 監査用 DuckDB 初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数を自動的に読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須変数は Settings 経由で取得（未設定時に明示的なエラー）

---

## 必要な環境変数（主要）

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI の API キー（score_news / regime 判定で必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu ステーション API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）（デフォルト: INFO）

設定は .env / .env.local に書いてプロジェクトルートに置くと自動読み込みされます。
自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）

1. Python 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   - 最低限必要な依存パッケージ:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt を用意している場合はそちらを使用してください:
     ```
     pip install -r requirements.txt
     ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルの環境変数に必要値を設定してください。
   - OpenAI / J-Quants のキーは機密情報なので CI や運用環境での管理に注意してください。

4. DuckDB データベースの用意
   - デフォルトは `data/kabusys.duckdb`。settings.duckdb_path で変更可能。
   - 監査ログ専用 DB を初期化する場合:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（例）

以下はライブラリを直接使う基本的な例です。実行前に環境変数や .env を適切に設定してください。

- 日次 ETL を実行する（prices / financials / calendar を差分更新し品質チェック）
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（指定日分）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続
count = score_news(conn, date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ma200 + マクロニュース LLM）
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, date(2026, 3, 20))
```

- 監査スキーマの初期化（既存 DuckDB 接続へ追加）
```py
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ニュース RSS を取得して DB に保存するワークフローは news_collector モジュールを参照してください（fetch_rss / preprocess_text 等）。

---

## 注意・設計上のポイント

- Look-ahead バイアス回避:
  - 内部処理は target_date を引数で受け、datetime.today() / date.today() を直接参照しない設計（バックテストでの先行取得防止）。
  - J-Quants の取得時には fetched_at を記録し「いつそのデータを知得したか」をトレース可能にしています。
- フェイルセーフ:
  - OpenAI API の失敗時やネットワークエラーは多くの場合にフォールバック（例: macro_sentiment = 0.0）して処理を継続します。
- セキュリティ:
  - news_collector では SSRF 対策（スキーム/プライベートアドレスの除外、リダイレクト検査）、受信サイズ制限、defusedxml による XML の安全パースを実施しています。
- 冪等性:
  - J-Quants データ保存・ETL は基本的に冪等（INSERT … ON CONFLICT DO UPDATE / DELETE→INSERT の置換）を意識しています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys 配下を抜粋）

```
src/kabusys/
├─ __init__.py                # パッケージ情報
├─ config.py                  # 環境変数・設定管理
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py             # ニュース NLP（score_news）
│  └─ regime_detector.py      # 市場レジーム判定（score_regime）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py       # J-Quants API クライアント + DuckDB 保存関数
│  ├─ pipeline.py             # ETL パイプライン（run_daily_etl 等）
│  ├─ etl.py                  # ETL 結果型公開
│  ├─ news_collector.py       # RSS 取得 / 前処理 / 保存ユーティリティ
│  ├─ calendar_management.py  # 市場カレンダー管理（is_trading_day 等）
│  ├─ quality.py              # データ品質チェック
│  ├─ stats.py                # 統計ユーティリティ（zscore_normalize）
│  └─ audit.py                # 監査ログスキーマ初期化 / init_audit_db
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py      # モメンタム / ボラティリティ / バリュー計算
│  └─ feature_exploration.py  # 将来リターン計算, IC, サマリー, rank
```

- その他、各モジュールに詳細な docstring と設計ノートが含まれており、実装意図や安全性（例外処理、リトライ、ログ出力）に関する説明があります。

---

## 開発・テストについて

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テスト時に自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分はテストで差し替え（モック）しやすいように `_call_openai_api` 等の関数を定義しています。
- DuckDB に対する executemany の空リスト取り扱い等、実行時の互換性に注意するコードが含まれます（DuckDB のバージョン差分対応）。

---

何か追加で README に載せたい点（例: CI の設定例、より詳細な使用例、SQL スキーマ定義の抜粋など）があれば教えてください。
# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などをモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（date/target_date を明示的に扱う）
- DuckDB をデータストアとして想定（ローカルファイルまたはメモリ）
- API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- 冪等性（ETL 保存や監査ログ初期化など）は重視する

---

## 機能一覧

- データ
  - J-Quants からの株価日足 / 財務 / 上場情報 / JPX カレンダー取得（jquants_client）
  - ETL パイプライン（差分取得、backfill、品質チェック）（data.pipeline）
  - ニュース収集（RSS → raw_news）（data.news_collector）
  - 市場カレンダー管理・営業日判定（data.calendar_management）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）（data.quality）
  - 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ（data.audit）
  - 汎用統計ユーティリティ（z-score 正規化）（data.stats）

- AI / NLP
  - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に保存（ai.news_nlp）
  - マクロニュース（ETF 1321 の MA200 乖離 + マクロセンチメント）を合成して市場レジーム（bull/neutral/bear）を日次判定（ai.regime_detector）

- Research（研究用）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等（research.feature_exploration）
  - zscore_normalize（data.stats を再利用）

- 設定管理
  - 環境変数から設定を読み込むユーティリティ（config）。プロジェクトルートの `.env` / `.env.local` を自動的に読み込む（無効化可能）。

---

## 動作要件

- Python 3.10 以上（型ヒントに `|` を使用）
- 主要依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード 等）

必要なパッケージはプロジェクトの packaging によりますが、簡単なインストール例は次の通りです。

例（仮想環境の作成・依存インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# またはプロジェクトに setup.py/pyproject があれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して依存関係をインストールする（上記参照）

3. 環境変数を用意する
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと、パッケージ import 時に自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 主に必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL : kabuAPI のベース URL（任意、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
     - OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : SQLite（monitoring 用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV : one of development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリの作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトでの簡単な利用例です。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（None なら今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを算出して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数で設定するか、api_key に渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（MA200 とマクロニュースの合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB を初期化（別 DB ファイルで管理するのがおすすめ）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセス可能
```

- 環境設定へのアクセス（コード内で）
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)   # 必須: 未設定なら ValueError
print(settings.kabu_api_base_url)       # デフォルト http://localhost:18080/kabusapi
print(settings.is_live, settings.is_paper, settings.is_dev)
```

---

## 自動 .env ロードの動作

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を持つ親ディレクトリ）を探索して `.env` → `.env.local` の順で読み込みます。
- 読み込み順は OS 環境変数 > .env.local > .env です（.env.local が既存の OS 環境変数を上書きしないよう保護されます）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

.env のパースはシェル形式の簡易サポート（`export KEY=value` / 引用符 / 行コメント）に対応しています。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールの一覧（src/kabusys 以下）。実際のリポジトリには他ファイルがある可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py            -- 市場レジーム判定（ETF1321 MA200 + マクロ）
  - data/
    - __init__.py
    - calendar_management.py        -- マーケットカレンダー管理・営業日判定
    - etl.py                        -- ETL 公開インタフェース（ETLResult）
    - pipeline.py                   -- 日次 ETL パイプライン
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログスキーマ初期化
    - jquants_client.py             -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py             -- RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py        -- 将来リターン / IC / 統計サマリー

---

## 運用・注意点

- OpenAI の呼び出しは API 料金が発生します。API キーは適切に管理してください。
- J-Quants の API 利用にはトークンが必要です（JQUANTS_REFRESH_TOKEN）。
- ETL / データ取得処理はレート制限やリトライを含みますが、長時間の実行や大量データ取得では API 制限に注意してください。
- DuckDB を用いることでローカルで高速に分析できますが、運用用途ではバックアップやファイルパス管理に注意してください。
- 監査ログ（audit テーブル）は削除しない前提で設計されています。運用上の保管・ローテーション方針を検討してください。

---

## コントリビューション

バグ報告や改善提案は issue を通じてお願いします。コード変更は PR で送ってください。テストやドキュメントの追加歓迎します。

---

必要であれば、README にサンプル .env.example や詳細なコマンド（cron / systemd を使ったバッチ実行例、監視方法、Slack 通知の使い方等）を追加できます。どの部分を詳細化したいか教えてください。
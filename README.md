# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けライブラリ群です。  
データの ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP による銘柄センチメント算出、マーケットレジーム判定、研究用のファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 日次 ETL（prices, financials, market calendar）の差分取得 / 保存
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集 / NLP
  - RSS フィードからのニュース収集（SSRF 対策・トラッキング削除・サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（batch 処理・JSON mode）
  - 市場マクロニュースを踏まえた市場レジーム判定（ETF 1321 の MA200 と LLM スコアを合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- カレンダー管理
  - JPX カレンダー（market_calendar）を管理し営業日判定・次営業日/前営業日取得等を提供
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック機能（QualityIssue を返す）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化
  - 監査DB の初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - 環境変数（.env / .env.local）の自動ロード（プロジェクトルート検出）と Settings オブジェクト

---

## 必要条件 / 依存ライブラリ

- Python 3.10+（型注釈の Union | 等を利用）
- 主要依存（抜粋）
  - duckdb
  - openai
  - defusedxml

プロジェクトの pyproject.toml / requirements.txt を用意している想定です。ローカルでの動作確認時は上記パッケージをインストールしてください。

例:
```bash
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 開発用なら package を編集可能インストール
python -m pip install -e .
```

---

## 環境変数 / .env

このプロジェクトは環境変数から設定を読み込みます。自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を見つけ、`.env` → `.env.local` の順で読み込みます（`.env.local` は上書き）。

自動ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須・代表的な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション等のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）

.env 形式のパース仕様は柔軟で、export プレフィックスやクォートを扱います。`.env.example` を参考に `.env` を作成してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存関係をインストール
   ```bash
   pip install -r requirements.txt   # または必要なパッケージを個別インストール
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` として必要な値を配置（例は下）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=CXXXXX
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. (オプション) DuckDB 初期スキーマ / 監査DB の初期化
   - 監査DB を作成:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```

---

## 使い方（主な API）

以下は代表的な使い方例です。実行は Python スクリプトやバッチ内で行います。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント算出（OpenAI API キーは環境変数か引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))
print("scored:", n_written)
conn.close()
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
conn.close()
```

- 監査スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用ユーティリティ例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(records[:5])
```

- カレンダー関連
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

注意点:
- 多くの関数は Look-ahead bias を防ぐために内部で `date.today()` を参照しない設計です。`target_date` を明示的に渡すことが推奨されます（特にバックテストや研究用途で重要）。
- OpenAI 呼び出しを行う機能は API キーを必要とします（引数で注入可能。テストではモック可能な設計）。
- DuckDB に対しては BEGIN / DELETE / INSERT / COMMIT のような冪等書き込みを行う部分があり、トランザクション管理は関数ごとに扱われています。

---

## ディレクトリ構成 (主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env ロード、自動検出、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースのセンチメント計算（OpenAI 呼び出し、バッチ処理）
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / rate limiter / retry）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック（QualityIssue）
    - stats.py — zscore_normalize（共通統計ユーティリティ）
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - その他: strategy, execution, monitoring パッケージが __all__ に含まれる想定（コードベース拡張）

---

## 設計方針 / 注意点（概要）

- Look-ahead bias 回避を重要視：内部のデータ取得や計算は target_date 未満のデータのみを使う等の設計を採用。
- フェイルセーフ：API 失敗時は例外で全停止よりも安全側のフォールバック（スコア 0.0、処理スキップ等）で継続する設計が多い。
- 冪等性：ETL および保存処理は可能な限り冪等（ON CONFLICT）で実装。
- テスト容易性：外部呼び出し（OpenAI, HTTP 等）は関数をモックできるように設計。
- セキュリティ：news_collector に SSRF 対策（ホスト検査 / リダイレクト検査）、defusedxml の使用、レスポンスサイズ上限などの防御策を実装。

---

## 開発 / テストについて

- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます（ユニットテストで便利）。
- OpenAI / J-Quants など外部 API 呼び出し箇所はモック可能に実装されています（ユニットテストでは patch して検証可能）。
- DuckDB をインメモリで接続して単体テストを行うことができます（db_path=":memory:" を使用）。

---

## 連絡 / 貢献

バグ報告や改善提案は issue を立ててください。Pull Request は歓迎します。  
セキュリティ関連の問題がある場合は公開 issue を避け、まずリポジトリ管理者に直接連絡してください。

---

README は以上です。必要であれば、導入例（docker-compose、systemd ジョブ、サンプル .env.example、CI 設定）や API リファレンス（各関数の引数・戻り値一覧）を追加で作成します。どの部分を詳しく出力しますか？
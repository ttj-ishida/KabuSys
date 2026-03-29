# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB ベースのデータストア、J-Quants 経由の ETL、ニュース収集・NLP（OpenAI）によるスコアリング、マーケットカレンダー管理、研究用ファクター計算、監査ログ（取引トレース）などを包含します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定
  - .env / .env.local から自動的に環境変数を読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須環境変数取得ヘルパーを提供（`kabusys.config.settings`）

- データ ETL（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - レート制御、リトライ、トークン自動リフレッシュ対応
  - 日次 ETL エントリポイント（`run_daily_etl`）

- ニュース収集 / NLP（OpenAI）
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - ニュースを銘柄別に集約して OpenAI（gpt-4o-mini）に JSON Mode で投げ、センチメント/ai_score を `ai_scores` に格納（`score_news`）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメントを合成、`score_regime`）

- データ品質チェック
  - 欠損、重複、スパイク、日付整合性などのチェック（`data.quality`）

- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（情報係数）、統計サマリ、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution を UUID ベースでトレース可能にする監査テーブル定義／初期化（`data.audit`）

---

## 必須環境変数（主要）

以下はこのコードベースで参照される主な環境変数の例です（`.env.example` を作成して管理してください）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabu ステーション用パスワード
- KABU_API_BASE_URL（任意）: デフォルト `http://localhost:18080/kabusapi`
- SLACK_BOT_TOKEN（必須）: Slack 通知用（本コード中で参照）
- SLACK_CHANNEL_ID（必須）
- DUCKDB_PATH（任意）: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH（任意）: デフォルト `data/monitoring.db`
- KABUSYS_ENV（任意）: `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL（任意）: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`
- OPENAI_API_KEY（OpenAI 呼び出しを使う場合は必須）: OpenAI API キー

自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必要要件（依存）

- Python 3.10+
- ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （ネットワーク系は標準 urllib を使用）
- （必要に応じて）slack-sdk 等の通知用ライブラリ

インストール例（仮）:
pip install duckdb openai defusedxml

※ packaging（setup/pyproject）に依存している場合はそちらを参照して下さい。

---

## セットアップ手順

1. リポジトリをクローン/取得

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上の依存を個別にインストール）

4. .env を作成
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必須環境変数を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

   自動読み込み: このライブラリは起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。

5. DuckDB データベースのディレクトリを作成（必要であれば）
   mkdir -p data

---

## 使い方（主要ユースケース）

以下は Python スクリプトや REPL から呼び出す例です。

- DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価/財務/カレンダー + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアリング（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None なら環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 生成された conn_audit に対して監査用の INSERT/SELECT を行う
```

- 設定（settings）利用例
```python
from kabusys.config import settings
print(settings.duckdb_path)      # Path オブジェクト
print(settings.is_live)          # bool
token = settings.jquants_refresh_token  # 必須の設定が無ければ ValueError
```

---

## 注意点 / 設計上の要所

- Look-ahead bias 回避:
  - ETL / スコアリング関数は内部で `date.today()` を無闇に参照せず、明示的に `target_date` を受け取るよう設計されています（バックテストでの使用を想定）。
  - prices_daily や news 取得クエリでは `date < target_date` や排他条件を用いるなどルックアヘッドを避けています。

- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE を用いて冪等に行われます。
  - ニュース保存や監査テーブルも冪等性・ユニーク制約に注意して実装されています。

- フェイルセーフ:
  - OpenAI 呼び出し失敗時はスコアを 0 にフォールバックするなど、外部 API 失敗でプロセスが停止しない設計です（ログ出力で通知）。

- セキュリティ / SSRF 対策:
  - RSS 取得時に URL スキーム検証、プライベート IP 判定、リダイレクト先検査、レスポンスサイズ上限、defusedxml を利用した XML パースなどの対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールのツリー（src/kabusys 配下の抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他 data 用ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (README に明記されていないが __all__ に含まれる可能性あり)
  - strategy/ (戦略層用、ここでは抜粋外)
  - execution/ (発注実行層、ここでは抜粋外)

※ 上記はコードベースに含まれる主要モジュールの一覧です。実際のリポジトリではさらに細かなファイルやテスト、スクリプトが含まれることがあります。

---

## 開発者向けヒント

- 自動 .env 読み込みの挙動は `kabusys.config` 内で実装されています。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分はユニットテスト容易化のために `_call_openai_api` を patch して差し替え可能です（`kabusys.ai.news_nlp._call_openai_api` など）。
- DuckDB による executemany の挙動（空リスト不可等）に注意している箇所があります（news / ai_scores 書き込み等）。

---

## ライセンス / 貢献

この README はコードベースの説明文書です。ライセンスやコントリビューション方法は別途リポジトリの LICENSE / CONTRIBUTING を参照してください。

---

質問があれば、使い方の具体例（ETL スケジュール設定、OpenAI プロンプト調整、監査ログの利用方法など）について詳しく補足できます。どの部分を詳しく知りたいですか？
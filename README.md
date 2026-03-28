# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（オーダー/約定トレーサビリティ）などのユーティリティ群を提供します。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API からの株価（日次OHLCV）・財務・市場カレンダー取得（ページネーション対応、リトライ、レート制御）
  - 差分更新・バックフィル機能
- データ品質管理
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す設計）
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF対策、トラッキング除去、前処理）
  - OpenAI を用いた銘柄ごとのニュースセンチメント（ai_scores）算出
- 市場レジーム判定
  - ETF(1321)の200日MA乖離とマクロニュースのLLMセンチメントを組み合わせて日次で 'bull'/'neutral'/'bear' を判定
- リサーチ用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC計算、Zスコア正規化 等
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルの初期化・管理（監査用 DuckDB スキーマ生成関数あり）
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings クラスによる環境変数アクセス

---

## 依存（概略）

主要な Python パッケージ（プロジェクトに requirements.txt があればそれを使用してください）:

- Python 3.9+
- duckdb
- openai
- defusedxml

（上記以外に標準ライブラリのみで動くモジュールも多数含まれます）

---

## セットアップ

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell等)
   ```

3. 必要パッケージをインストール（requirements.txt がある場合）

   ```bash
   pip install -r requirements.txt
   ```

   直接インストールする場合の例:

   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意する（.env または .env.local をプロジェクトルートに配置可能）。自動ロードは .git または pyproject.toml を基準にプロジェクトルートを検出して行われます。自動読み込みを無効化する場合は環境変数を設定します：

   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必須環境変数（例）

Settings クラスで参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベースURL（任意、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネルID（必須）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（任意、デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（任意、デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ('development'|'paper_trading'|'live')（任意、デフォルト development）
- LOG_LEVEL — 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（任意、デフォルト INFO）
- OPENAI_API_KEY — OpenAI 呼び出し時に使用（score_news / score_regime で参照）

.env のサンプル（README 用例）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要なユースケース）

以下はライブラリ関数の呼び出し例です。事前に DuckDB へ接続し、必要なテーブル・スキーマが用意されていることを前提とします。

- DuckDB に接続する例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）:

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI を使う）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY をセットしてください
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 戻り値 1 = 成功
```

- 監査ログ（Audit）スキーマ初期化:

```python
from kabusys.data.audit import init_audit_db
# ファイルベース DuckDB を作成し、監査テーブルを初期化して接続を返す
audit_conn = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算例:

```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 設定にアクセスする例:

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

注意:
- OpenAI を利用する機能は、API呼び出し時に rate/エラー処理を行いますが、APIキーは適切に管理してください。
- 多くの関数は「ルックアヘッドバイアス防止」の考慮（target_date より未来のデータを参照しない）をしているため、バックテスト運用にも配慮されています。

---

## DB スキーマについて

- 監査ログ（signal_events / order_requests / executions）は `kabusys.data.audit.init_audit_schema` / `init_audit_db` で初期化できます。
- その他のテーブル（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily 等）は ETL とともに使用されますが、本 README のコードベースには全スキーマ初期化関数が含まれていない場合があります。実行前に必要なテーブル定義を準備してください（プロジェクト内別ファイルやマイグレーションスクリプトを確認してください）。

---

## 自動 .env ロードの挙動

- 起点はこのパッケージの config モジュール内で、.git または pyproject.toml をプロジェクトルートと判定します。
- 自動ロード順序: OS 環境 > .env.local（上書き） > .env（下書き）
- テスト等で自動ロードを無効化する場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュール・ファイルを抜粋したツリー:

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
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他: pipeline に関連する ETL/quality/jquants クライアント等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (LLM 関連)
  - research/ (ファクター・リサーチ関連)

（実際のリポジトリは上記以外にもモジュールやサポートファイルが存在する場合があります。プロジェクトルートのファイルや pyproject.toml を参照してください。）

---

## 運用上の注意

- OpenAI / J-Quants の API キーは秘匿してください。共有リポジトリにハードコーディングしないでください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない前提の設計です。
- 本ライブラリは「実際の発注やブローカー接続」を内包する設計要素を持ちますが、発注処理・証券会社向けラッパーは別モジュール（execution や外部ブリッジ）で実装する想定です。実稼働での発注は十分にテスト・安全対策を行ってください。
- 設計上、ETL や AI 呼び出しで API エラーが起きてもフェイルセーフ（スコア=0 等）で継続する部分があります。運用時はログ・監視を必ず組み合わせてください。

---

## 貢献 / 開発

- コードを修正したらユニットテスト・静的解析を行ってからプルリクエストしてください。
- 自動 .env 読み込みが問題を起こす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト実行してください。

---

以上です。実際の運用や導入で不明点があれば、どの機能をどう使いたいかを教えてください。具体的な利用シナリオに合わせた使用例や初期化スクリプト例を追加で作成します。
# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（部分実装）。  
DuckDB ベースのデータプラットフォーム、J-Quants 連携の ETL、ニュース NLP（OpenAI）を用いた銘柄センチメント評価、研究用ファクター計算、監査ログスキーマなどを提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（.env / 自動読み込み）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は、日本株のデータ収集・品質チェック・特徴量作成・シグナル→発注の監査トレーサビリティまでのコンポーネント群を想定したライブラリです。本リポジトリには以下の要素が含まれます（抜粋）:

- J-Quants API クライアント（取得・保存、ページネーション、トークン管理、レート制御）
- ETL パイプライン（価格・財務・カレンダーの差分取得、品質チェック）
- ニュース収集（RSS）およびニュース NLP（OpenAI を利用した銘柄別センチメント）
- 市場レジーム判定（ETF + マクロニュースの LLM 結果を組み合わせ）
- 研究向けファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 等）
- 監査ログスキーマ（signal / order_request / execution のテーブル群）

設計上の特徴として、バックテストでの Look-ahead バイアス防止、冪等保存、外部 API のリトライ・レート制御、DuckDB ベースの効率的なクエリを重視しています。

---

## 主な機能一覧
- データ取得
  - J-Quants から株価日足、財務データ、JPX カレンダーを取得（jquants_client）
  - RSS 収集（news_collector.fetch_rss）
- ETL
  - 差分取得と DuckDB への冪等保存（data.pipeline.run_daily_etl 等）
  - 品質チェック（data.quality）
- AI / NLP
  - ニュースを LLM で銘柄別センチメント化（ai.news_nlp.score_news）
  - マクロニュース + ETF の MA 乖離を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- 研究（research）
  - モメンタム/ボラティリティ/バリュー等のファクター計算（research.factor_research）
  - 将来リターン・IC・統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査（audit）
  - signal_events / order_requests / executions 用のスキーマ初期化（data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み、環境変数ラッパー（config.Settings）

---

## セットアップ手順

1. リポジトリをクローンしてインストール
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な Python パッケージ（主な依存例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外は requirements.txt を用意している場合はそれを利用してください）

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（下記参照）。開発ではプロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. DuckDB データベース用ディレクトリを作成する（デフォルトは data/）
   ```
   mkdir -p data
   ```

---

## 環境変数（.env の例）

config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで参照）

サンプル `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を基準）を検出して `.env`、`.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` の上書きになります。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの簡単な利用例です。DuckDB に適切なテーブル定義がある前提です（ETL による初期作成等）。

- DuckDB 接続を作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次）実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（指定日のニュースを解析し ai_scores に保存）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY 環境変数を設定済みであれば api_key 引数は不要
count = score_news(conn, date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20))  # market_regime テーブルへ書き込みを行う
```

- 監査ログスキーマ初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 監査用に独立 DB を作る
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- ai モジュールは OpenAI API を呼び出します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しはレート制限（既定 120 req/min）やトークンリフレッシュのロジックを含みます。J-Quants のリフレッシュトークンは JQUANTS_REFRESH_TOKEN に設定してください。
- 多くの関数は Look-ahead バイアス回避のため date 引数を受け取り、内部で日時(今)を直接参照しない設計です。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュールとその概要です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 読込、Settings クラス（J-Quants トークン、Kabu パスワード、Slack、DB パス、環境設定など）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの窓幅計算、OpenAI を使った銘柄別センチメント取得、ai_scores への書き込み
    - regime_detector.py
      - ETF(1321) MA200 乖離とマクロニュース LLM スコアを組み合わせて market_regime を算出
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・トークン管理・レート制御）
    - pipeline.py
      - ETL のメイン処理（run_daily_etl、run_prices_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・記事 ID 正規化・SSRF 対策等
    - calendar_management.py
      - market_calendar の更新・営業日判定ユーティリティ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ用 DDL / スキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（スピアマン）や統計サマリー

各ファイル内に詳細なドキュメント（docstring）があり、関数の引数や挙動、設計方針／注意点が記載されています。利用時は該当モジュールの docstring を参照してください。

---

## 補足 / 注意事項
- OpenAI / J-Quants / kabu ステーション等の外部サービス連携部分は実運用での取り扱いに注意してください（API キー管理、コスト、レート制限）。
- DuckDB のバージョン差異により一部バインド挙動（executemany の空リスト等）に注意が払われています。ライブラリ側でも互換性を保つための工夫が入っています。
- ニュース収集では SSRF や XML インジェクション対策（defusedxml、ホスト検査、レスポンスサイズ制限等）を行っていますが、運用環境に応じた追加の制御を推奨します。
- この README はコードベースの抜粋に基づくものです。実際の運用や拡張の際は、各モジュールの docstring と型注釈を参照してください。

---

必要なら、インストール用の requirements.txt、実行例スクリプト、初期スキーマ作成 SQL のサンプルなど追加で README に追記します。どの情報を優先して追加しますか？
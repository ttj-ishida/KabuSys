# KabuSys

KabuSys は日本株向けのデータプラットフォームとシグナル生成 / 解析用ライブラリ群です。J-Quants API からの ETL、ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含む自動売買・リサーチ基盤のコンポーネントを揃えています。

主な設計方針：
- ルックアヘッドバイアスを避ける（date / target_date を明示的に扱う）
- DuckDB を中心に SQL と Python の組合せで実装
- 外部 API 呼び出しはリトライやレート制限、フェイルセーフを備える
- 冪等性（ETL 保存や監査ログ初期化）を重視

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価（日足）・財務データ・市場カレンダーの差分取得と DuckDB への保存（冪等）
  - 差分更新やバックフィルのサポート、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、本文前処理、SSRF 対策、記事ID生成、raw_news への保存支援
- ニュース NLP（OpenAI）
  - 銘柄ごと・時間ウィンドウで集約したニュースを LLM に投げてセンチメント（ai_score）を算出・保存
  - マクロニュースのセンチメントと価格指標（ETF 1321 の MA200 乖離）を合成した市場レジーム判定
- リサーチ / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン計算、スピアマン IC、統計サマリー（rank, zscore など）
- 監査ログ（Audit）
  - signal_events, order_requests, executions などの監査テーブル定義、初期化ユーティリティ
- 設定管理
  - .env または環境変数からの設定読み込み（自動ロード、優先順位: OS > .env.local > .env）
  - 必須パラメータ未設定時は明瞭なエラー

---

## 必要条件（推奨）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml

最小限の依存はモジュールごとに異なります。上記はこのコードベースで明示的に使われている主要パッケージです。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時はパッケージをインストール（プロジェクトルートに pyproject.toml/setup.py がある前提）
pip install -e .
```

---

## 環境変数（主なもの）

config.Settings で参照される主要項目：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 bot token（プロジェクトで使用する場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化（テスト用）

自動 .env ロードの優先順:
1. OS 環境変数
2. .env.local（上書き可能）
3. .env（未設定のキーのみ）

Settings は未設定の必須キーに対して ValueError を投げます。.env.example の用意を推奨します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くか OS 環境で設定）
   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB を使う場合はデータディレクトリを作成（多くの初期化関数が自動作成しますが念のため）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なユースケース例）

以下は Python REPL / スクリプトからの呼び出し例です。target_date はルックアヘッドを防ぐため必ず明示してください。

- DuckDB 接続を開く（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（カレンダー / 価格 / 財務 / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} codes")
```
- 市場レジーム（macro + MA200）を計算して market_regime に保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key 省略時は OPENAI_API_KEY を参照
```

- 監査 DB を初期化（独立 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または既存 conn にスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ファクター計算 / リサーチ関数例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns

res_mom = calc_momentum(conn, date(2026,3,20))
res_fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
```

- テスト時の .env 自動ロード無効化
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 注意点 / 実装上の特徴

- 日付・時間の扱い：多くの処理は date/target_date を明示的に受け取り、datetime.today() や date.today() に依存しない設計（ルックアヘッドバイアス回避）。
- OpenAI 呼び出し：gpt-4o-mini を想定し JSON mode を利用。429/ネットワーク障害/タイムアウト/5xx に対してリトライを実装。API 失敗時はフェイルセーフ（スコア=0 等）で継続。
- J-Quants クライアント：固定間隔レートリミッタ、トークン自動リフレッシュ、ページネーション対応、保存は ON CONFLICT DO UPDATE により冪等性を確保。
- News Collector：SSRF 対策、受信バイト上限、gzip 解凍チェック、URL 正規化、トラッキングパラメータ除去、DefusedXML 使用による安全な XML パース。
- DuckDB に対する executemany など、バージョン差異や制約（空リスト不可など）を考慮した実装。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py （パッケージ定義）
  - config.py — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores へ保存）
    - regime_detector.py — ETF 1321 MA200 とマクロニュースを合成する市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
    - etl.py — ETLResult の再エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py — RSS 取得・前処理・保存サポート
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（実際のリポジトリのルートに pyproject.toml / setup.py / requirements.txt があると便利です）

---

## 開発・拡張のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化し、テストごとに環境を明確に制御するのが便利です。
- OpenAI 呼び出しや http open を行う箇所は関数単位でモックしやすく設計されている（内部の _call_openai_api / _urlopen を差し替え可能）。
- DuckDB スキーマ初期化や監査スキーマは冪等に設計されているため、CI/CD の初期セットアップやローカルでの反復実行が容易です。
- ETL の run_daily_etl は部分失敗にも耐える実装なので、問題検出後に再実行して回復させるワークフローを作ることを推奨します。

---

もし README にサンプル .env.example、CI 手順、より詳細な API リファレンスやコマンドラインツール用の使い方（例: CLI スクリプト）を追加したい場合は、どのレベルの詳細を期待するか教えてください。必要に応じてサンプルの .env.example やユニットテストの記述例も作成します。
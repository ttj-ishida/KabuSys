# KabuSys

日本株を対象とした自動売買 / データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ、そして OpenAI を使ったニュースセンチメント／市場レジーム判定までを含むモジュール群を提供します。

---

## 特徴（概要）

- J-Quants API 経由で株価（日次）・財務データ・上場情報・マーケットカレンダーを差分取得・保存
- ETL パイプライン（差分取得、保存、品質チェック）を一括実行
- RSS ベースのニュース収集（SSRF 対策・トラッキング削除・サイズ制限）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）および市場レジーム判定
- 研究用ユーティリティ：モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（signal_events / order_requests / executions）用のスキーマ初期化ユーティリティ
- DuckDB を利用したローカルデータストア設計
- フェイルセーフ・リトライ・レートリミット・ルックアヘッドバイアス対策などの実装方針に準拠

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・リトライ・レートリミッティング）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策）
  - calendar_management: 市場カレンダーの運用・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログのスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- ai
  - news_nlp: ニュースの銘柄別センチメント解析（score_news）
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM スコアを合成した市場レジーム判定（score_regime）
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: .env 自動読み込み（プロジェクトルート検出）、Settings クラス（環境変数定義）

---

## 必要条件

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK を利用）
- defusedxml（RSS パース時の安全対策）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

（インストールは下記セットアップ参照）

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング等用）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に `1` を設定

設定はプロジェクトルートに置かれる `.env` / `.env.local` ファイルまたは OS 環境変数から読み込みます。`.env.local` は `.env` をオーバーライドします。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone …

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -e .     （パッケージが setup.cfg / pyproject.toml に定義されている想定）
   - または必要なパッケージを個別に:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記の必須キーを設定してください。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードをテストで無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース準備（監査ログなど）
   - 監査用 DB を初期化する例は下記「使い方」を参照

---

## 使い方（簡単なコード例）

基本は DuckDB の接続を作成し、各公開 API を呼び出します。

- 設定と接続の準備
```python
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キー必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を用いる）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（別ファイルを推奨）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# init_audit_db はテーブルを作成して接続を返します
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は各銘柄ごとの dict のリスト
```

注意点:
- score_news / score_regime は OPENAI_API_KEY を参照します。api_key を引数で直接渡すことも可能です。
- ETL / API 呼び出しはネットワーク・API レート制限やリトライを考慮した実装になっています。

---

## 推奨ワークフロー（運用例）

1. 毎朝（ジョブ）: run_daily_etl を実行してデータ更新と品質チェック
2. ETL 後: ai.score_news を実行して当日分ニューススコアを生成
3. 市況判断: ai.score_regime を実行して市場レジームを更新
4. 戦略実行（別モジュール）: 監査ログ table を使ってシグナル→発注→約定 の追跡

---

## 設計上の注意 / セキュリティ

- RSS 収集には SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）を実装しています。
- J-Quants クライアントはレート制限（120 req/min）とリトライを実装済み。401 は自動リフレッシュ処理があります。
- OpenAI 呼び出しは JSON モードを用い、パース失敗や API 障害時はフェイルセーフ（0.0 のスコア等）で継続します。
- ルックアヘッドバイアス防止のため、各モジュールは target_date を明示的に受け取り、現在時刻を直接参照しない設計です。

---

## ディレクトリ構成（主なファイル/モジュール）

- src/kabusys/
  - __init__.py                      — パッケージ初期化、__version__
  - config.py                         — 環境変数 / Settings の管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch / save）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — マーケットカレンダー管理 / 営業日判定
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログスキーマ初期化
    - stats.py                         — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py              — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・テストに関するヒント

- 自動 .env 読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出し部分は内部で個別のラッパー関数を使っているため、ユニットテスト時は該当関数を patch してモックできます（例: kabusys.ai.news_nlp._call_openai_api や kabusys.data.news_collector._urlopen など）。
- DuckDB の executemany に関する挙動（空リスト不可）を考慮して実装されています。テストでも同様の制約があります。

---

## ライセンス / コントリビューション

（この README はコードベースの抜粋に基づいて作成しています。ライセンス情報や貢献ルールはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。）

---

必要であれば、README に CLI 例や systemd / cron の定期実行テンプレート、.env.example の雛形や SQL スキーマ初期化コマンドのサンプルなどを追記します。どの部分を詳しく追加しますか？
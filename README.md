# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、研究（ファクター算出）、AI ベースのニュースセンチメント評価、監査ログ等を備えた自動売買支援ライブラリです。本リポジトリは DuckDB をデータ層に用い、J-Quants API や OpenAI（GPT 系）を外部サービスとして利用する設計になっています。

主な目的:
- 市場データ・財務データ・マーケットカレンダーの ETL
- ニュース収集と LLM による銘柄センチメント算出
- 市場レジーム判定（マクロ × 価格指標の合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## 機能一覧

- data/
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - J-Quants API クライアント（認証、取得、DuckDB への保存、レート制御、リトライ）
  - ニュース収集（RSS → raw_news、SSRF 対策、正規化）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA 値とマクロニュースセンチメントを合成して market_regime に保存
  - 両モジュールとも OpenAI の JSON Mode を使用し、レスポンスのバリデート・リトライ実装あり
- research/
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic（Spearman rank IC）, factor_summary, rank
- config.py
  - .env（プロジェクトルート）または環境変数から設定を自動ロード（OS 環境変数優先）
  - 必須設定の取得ヘルパー（例: JQUANTS_REFRESH_TOKEN）
- audit モジュール
  - 監査テーブルの初期化 / 専用 DB 作成ユーティリティ

（注）execution / monitoring 関連の公開 API はパッケージ定義に含まれますが、実装は本スナップショットに含まれていない場合があります。

---

## 必要要件（推奨）

- Python 3.10+
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m pip install duckdb openai defusedxml
# 又は開発時
python -m pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env を準備（プロジェクトルートに配置）
   - このライブラリはプロジェクトルートを .git または pyproject.toml を基準に自動検出し、.env（および .env.local）を自動ロードします。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: 簡易 .env（実運用では秘密情報は適切に管理してください）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

主な設定キー（Settings から参照）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（オプション; デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY（ai モジュール利用時必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（プロセス監視用）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視）

---

## 初期化・簡単な使い方

以下は Python REPL あるいはスクリプトからの呼び出し例です。いずれも DuckDB 接続オブジェクト（duckdb.connect）を渡して操作します。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ用 DB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でインメモリ可
```

3) 日次 ETL 実行（例: 今日までの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュースセンチメント評価（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

5) 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

6) 研究系ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

注意:
- AI 関連関数は OpenAI API キー（OPENAI_API_KEY）を環境変数か引数で渡す必要があります。
- ETL の J-Quants 認証は settings.jquants_refresh_token を用いて内部で get_id_token() を実行します（自動トークン更新ロジックあり）。

---

## 実装上のポイント・設計ノート

- .env ロード:
  - 自動ロード順: OS 環境変数 > .env.local > .env
  - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して検出
  - 自動ロード停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- LLM 呼び出し:
  - OpenAI の JSON Mode（gpt-4o-mini 等）を利用しレスポンスを厳密に検証
  - レート／ネットワークエラーに対して指数バックオフのリトライを実装
  - API エラー時はフェイルセーフ（多くの場面でデフォルト値で継続）
- データの冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等性を担保
- Look-ahead バイアス対策:
  - 各処理で date 引数を明示的に受け取り、内部で今日() を参照して未来情報を参照しないよう配慮
- セキュリティ:
  - news_collector は SSRF 対策、XML の defusedxml 利用、受信サイズ制限、トラッキングパラメータ除去等を実装

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとした主要モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (他: execution/, monitoring/ はパッケージ公開名にはあるものの本スナップショットでの実装は限定的)

各モジュールの役割は上の「機能一覧」およびコード内ドキュメンテーションに詳述しています。関数／クラスには docstring が付与されているため、API 利用時にはそちらも参照してください。

---

## よくある作業例（メモ）

- ETL を cron / Airflow で定期実行する場合:
  - run_daily_etl(conn, target_date=today) を呼び出す前に settings を環境ごとに切り替える
  - ETLResult の has_errors / has_quality_errors を監視して通知や復旧処理を行う
- 監査 DB 初期化:
  - init_audit_db(path) を一度実行しておく（ファイルの親ディレクトリは自動作成される）
- OpenAI のコスト／レート管理:
  - バッチサイズや記事トリム設定（_BATCH_SIZE, _MAX_CHARS_PER_STOCK）を調整する

---

## サポート / 貢献

- コードの変更やバグ修正は PR で送ってください。各モジュールはテスト可能な小さな関数に分割されています（モックを使ったユニットテストがしやすい設計）。
- セキュリティ関連（API キー漏洩、SSRF、XML）には注意して実運用してください。

---

README は簡易ガイドです。詳細は各モジュールの docstring とコードコメント（日本語）を参照してください。質問があれば具体的なユースケース（ETL のスケジューリング、OpenAI の利用制限、DuckDB の初期スキーマ等）を教えてください。必要に応じて使用例やスニペットを追加します。
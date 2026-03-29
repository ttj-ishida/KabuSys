# KabuSys

日本株向けのデータプラットフォーム + 自動売買補助ライブラリです。  
J-Quants からのデータ取得（株価・財務・市場カレンダー）、ニュース収集・NLP、ファクター計算、ETL パイプライン、監査ログ（発注〜約定のトレース）など、マーケットデータ処理・調査・運用に必要な機能群を提供します。

設計上の特徴：
- DuckDB をデータ層に採用（軽量かつ高速な分析向け OLAP）
- ETL / 保存処理は冪等（ON CONFLICT / upsert）を重視
- 外部 API 呼び出しはリトライ・レート制御を実装（指数バックオフ等）
- バックテスト用の Look‑ahead バイアス対策（date.today()/datetime.today() を直接参照しない等）
- AI 呼び出しは JSON モードで厳密にパースし、失敗時はフェイルセーフ（ゼロ値等）で継続

---

## 主な機能一覧

- data（データプラットフォーム）
  - jquants_client: J-Quants API から株価・財務・カレンダーを取得 / DuckDB に保存
  - pipeline / etl: 日次 ETL パイプライン（差分取得、保存、品質チェック）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS から記事収集、SSRF 対策、前処理、raw_news 保存ロジック
  - audit: 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化 等）
- ai（NLP / レジーム判定）
  - news_nlp.score_news: ニュース記事をまとめて LLM で銘柄別センチメントを算出し ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM 結果を合成して市場レジームを判定し market_regime に保存
- research（リサーチ用途）
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーション等を利用）
- DuckDB を使用可能な環境

1. レポジトリをクローン（プロジェクトルートに `src/` がある想定）
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt がない場合の代表例）
   ```
   pip install duckdb openai defusedxml
   # 他に必要なライブラリがあれば適宜追加してください
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数 / .env を準備  
   以下はいくつかの必須/推奨環境変数の例（プロジェクトでは .env を自動ロードします）。
   - 必須（設定が呼び出し時にチェックされる）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注系を使う場合）
   - 任意・デフォルトあり
     - KABUSYS_ENV — 開発環境: development / paper_trading / live（default: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、default: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB 等（default: data/monitoring.db）
     - OPENAI_API_KEY — OpenAI を利用する場合はここか 関数引数で渡す
   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   自動ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

注意: Settings クラスは必須変数未設定時に ValueError を送出します。

---

## 使い方（主要な例）

以下は最短で各主要機能を呼び出すサンプルです。実運用ではログ設定・例外処理・堅牢な起動スクリプトが必要です。

- settings（環境変数読み取り）
```python
from kabusys.config import settings

print(settings.duckdb_path)      # Path オブジェクト
print(settings.is_live)          # True / False
token = settings.jquants_refresh_token  # 必須が未設定だと例外
```

- DuckDB 接続例（監査 DB 初期化）
```python
import duckdb
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# ファイル DB を使用
conn = init_audit_db(settings.duckdb_path)
# または: conn = init_audit_db(":memory:")
```

- 日次 ETL 実行（パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written_count}")
```
OPENAI API キーは api_key 引数で渡すか環境変数 OPENAI_API_KEY を設定します。記事がない場合は早期終了します。

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- リサーチ用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

注意点:
- AI 呼び出しはネットワーク・API レートの影響を受けます。score_news / score_regime は失敗時に部分継続する設計です（ゼロやスキップでフォールバック）。
- jquants_client は内部でトークンキャッシュとリフレッシュを行い、レート制限（120 req/min）を守るためのスロットリングを実装しています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）
- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数および Settings クラス（.env 自動ロード機能含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（LLM 呼び出し、結果のバリデーション、ai_scores への保存）
  - regime_detector.py — 市場レジーム判定（ETF MA とマクロニュースの合成）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETL インターフェース（ETLResult の再エクスポート）
  - news_collector.py — RSS 収集、SSRF 対策、前処理、raw_news 保存ロジック
  - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック一式
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー、rank/summary utilities

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定  
  -> settings のプロパティ（例: settings.jquants_refresh_token）をアクセスすると必須変数がない場合に例外が発生します。.env をプロジェクトルートに置くか環境変数を設定してください。

- OpenAI 呼び出しが失敗している  
  -> OPENAI_API_KEY を設定するか、score_news/score_regime に api_key を渡してください。API サービス側の 5xx/429 は自動リトライ・バックオフを行いますが、最終的にフォールバック値（例: macro_sentiment=0.0）で継続します。

- J-Quants API リクエストの 401 エラー  
  -> settings.jquants_refresh_token が正しいか確認してください。jquants_client は 401 を検知するとトークンリフレッシュを試みます。

- RSS 取得で SSRF / 不正 URL が原因のエラー  
  -> news_collector は http/https 以外のスキームやプライベート IP 宛のアクセスを拒否します。ソース URL の確認をしてください。

---

## 開発・拡張上の注意

- DB スキーマやテーブルは DuckDB の SQL を使って作成・管理する想定です（audit.init_audit_schema などが DDL を提供）。
- 本リポジトリのコードは本番発注（実際の資金を動かす）に用いる場合、十分なレビュー・テスト・リスク管理が必要です。特に execution（発注）周りはリスクが高く、paper_trading / live モードの切替に注意してください。
- テスト時は自動環境読み込みを無効化できます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

必要であれば、README に「セットアップスクリプト例」「.env.example」「サンプル DB スキーマ作成 SQL」や「よく使う CLI ランナー例（ETL を Cron で回すサンプル）」などを追加します。どの点を詳細化したいか教えてください。
# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリセットです。  
DuckDB を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログスキーマ、ファクター計算・探索などを提供します。

---

## 主要な機能（概要）

- データ収集・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に格納
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS フィード取得と前処理（SSRF対策、URL正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）生成
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースの LLM センチメントを合成して日次レジーム判定
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査スキーマを DuckDB に初期化
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- ユーティリティ群
  - マーケットカレンダー管理（営業日判定／次営業日／前営業日／期間内営業日取得）
  - J-Quants クライアント：レート制限・リトライ・トークン自動リフレッシュ・ページネーション対応

---

## 前提条件 / 依存関係

最低限必要な外部パッケージ（プロジェクトの requirements を用意してください）：

- Python 3.10+
- duckdb
- openai
- defusedxml

（実コード内で urllib, json, datetime など標準ライブラリを広く利用）

例（pip）:
```bash
pip install duckdb openai defusedxml
```

※ プロジェクト化されている場合は requirements.txt / pyproject.toml を参照してインストールしてください。

---

## 環境変数（主なもの）

設定は環境変数またはルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（使う機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (instant|partial|never|reject) — Paper Trading の挙動
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は `kabusys.config.settings` 経由で参照できます。

---

## セットアップ手順（ローカルで試すための最低手順）

1. Python と pip を準備
2. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
3. リポジトリをクローン／配置し、プロジェクトルートに `.env` を作成
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検知して `.env` / `.env.local` を読み込みます。
4. DuckDB の DB ファイル用ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
5. （任意）監査 DB 初期化
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # conn を使って監査テーブルが作成されていることを確認できます
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリ関数を直接呼ぶ Python スニペット例です。実行環境に応じて API キーや DB パスを .env に設定してください。

- 日次 ETL 実行（株価／財務／カレンダーの差分取得 + 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores 生成）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（既存接続に追加）
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意:
- OpenAI 呼び出し（score_news / score_regime）は `OPENAI_API_KEY` を必要とします。関数呼び出し時に `api_key` を渡すことも可能です。
- データベーススキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）は ETL／初期化処理経由で整備してください（スキーマ作成コードは別モジュールにある前提です）。

---

## 自動 .env 読み込みについて（挙動）

- 実行時、`kabusys.config` はプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、`.env`（優先度低）および `.env.local`（優先度高）を読み込みます。
- OS 環境変数が優先され、`.env` のキーは上書きされません（`.env.local` は override=True のため上書き可。ただし既存 OS 環境変数は保護されます）。
- 自動ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env のパースはシェル風の記法（コメント、クォート、export プレフィックス）に対応しています。

---

## ディレクトリ構成（主要ファイルの説明）

簡易ツリー（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py                 -- 環境変数 / 設定管理
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py            -- ニュースの LLM スコア化（ai_scores へ保存）
│  └─ regime_detector.py     -- 市場レジーム判定（ma200 + マクロLLM）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py      -- J-Quants API クライアント（取得 + 保存）
│  ├─ pipeline.py            -- ETL パイプライン（run_daily_etl 等）
│  ├─ etl.py                 -- ETLResult 再エクスポート
│  ├─ news_collector.py      -- RSS 取得・前処理・保存ロジック
│  ├─ calendar_management.py -- 市場カレンダー管理（営業日判定等）
│  ├─ quality.py             -- データ品質チェック
│  ├─ stats.py               -- 汎用統計ユーティリティ（zscore 等）
│  └─ audit.py               -- 監査ログスキーマ初期化 / init_audit_db
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py     -- Momentum/Value/Volatility の計算
│  └─ feature_exploration.py -- forward returns / IC / summary / rank
└─ research/... (他ユーティリティ)
```

各ファイルは README 内の該当節で挙げた役割を持ち、DuckDB 接続を受け取って SQL と Python を組み合わせて処理します。

---

## 注意事項 / 推奨事項

- Look-ahead bias を避ける設計が意識されています（内部で date.today() を無暗に参照しない等）。バックテスト等で流用する際は対象日の扱いに注意してください。
- OpenAI API 呼び出しは外部サービスに依存するため、レート制限やコストに注意してください。エラー発生時はフェイルセーフで継続する実装になっていますが、結果の妥当性は確認してください。
- J-Quants API のレート制限（120 req/min）に従って _RateLimiter が制御します。大量取得時は時間がかかる点に留意してください。
- DuckDB のバージョンや SQL の振る舞いによっては executemany の扱い等に互換性差が出るため、環境を固定することを推奨します。

---

もし README に追加して欲しい箇所（例: CLI 実行方法、requirements.txt の実例、より詳細なスキーマ定義、運用フロー図 など）があれば教えてください。必要に応じてサンプル `.env.example` も作成します。
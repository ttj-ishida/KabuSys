# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）など、投資システムに必要なデータ処理・解析・監視の基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアス（未来情報参照）を避ける実装
- DuckDB を用いたローカルデータ管理（冪等保存・トランザクション処理）
- 外部 API 呼び出しには堅牢なリトライ/バックオフ制御
- エラーは基本的にフェイルセーフ（重要度に応じてログや戻り値で表現）
- テスト差し替え用に内部 API 呼び出しをモックしやすい設計

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得して保存（fetch / save）
  - 差分更新ロジック、バックフィル対応、品質チェック統合（quality モジュール）
  - run_daily_etl による日次 ETL の統合実行

- ニュース収集 / NLP
  - RSS フィード収集（安全対策: SSRF対策、トラッキングパラメータ除去、XML の安全パーサ）
  - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores に保存（score_news）

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュース（LLMによるセンチメント）を重み付けして日次レジーム判定（bull/neutral/bear）（score_regime）

- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ、Zスコア正規化

- カレンダー管理
  - JPX の市場カレンダー保存・検索（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）

- データ品質チェック
  - 欠損データ、スパイク検出、重複チェック、日付整合性チェック（run_all_checks）

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化および専用 DB 作成（init_audit_schema / init_audit_db）

- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート検出、無効化も可能）
  - settings オブジェクト経由で各種設定にアクセス可能

---

## セットアップ手順

前提
- Python 3.10 以上（| 型アノテーション等を使用）
- DuckDB を利用するため native 拡張は不要（pure Python パッケージで十分）

推奨インストール（例: pip）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他プロジェクト固有の依存があれば追加
```

環境変数 / .env
- プロジェクトルートの `.env` および `.env.local` が自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（使用されるキー）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite 等（既定: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV : environment ("development" | "paper_trading" | "live"), 既定 "development"
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)

例 `.env`（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

データベース初期化（監査DB の例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
```

---

## 使い方（主要な API と実行例）

以下は典型的な利用シナリオの例です。実行は Python スクリプトやバッチ（cron / systemd timer）などから行います。

1) DuckDB 接続を用意して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（AI スコア）を計算して ai_scores テーブルへ保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored:", n_written)
```

3) 市場レジーム判定を行い market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

4) 監査スキーマの初期化（既存接続へテーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)
```

5) 研究用ファクター計算、正規化、IC 解析
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
date_ = date(2026,3,20)
mom = calc_momentum(conn, date_)
fwd = calc_forward_returns(conn, date_)
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
```

注意点
- OpenAI 呼び出しを行う関数は API キーを引数で渡せます（テストやキー管理上の柔軟性）。
- ETL / API 呼び出しはネットワークエラーや API レート制限を考慮したリトライ実装がありますが、実運用ではログとモニタリングを併用してください。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリルートの想定： src/kabusys 以下にモジュール群が配置されています。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）とエクスポートモジュールリスト

- src/kabusys/config.py
  - .env / .env.local 自動ロード、settings オブジェクト（各種設定・パス・閾値など）

- src/kabusys/ai/
  - news_nlp.py : ニュースを銘柄別に集約し OpenAI でセンチメントを算出、ai_scores に保存（score_news）
  - regime_detector.py : ETF 1321 の MA 乖離とニュースセンチメントを合成して market_regime を作成（score_regime）

- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（fetch / save / 認証 / rate limit / retry）
  - pipeline.py : ETL パイプライン（run_daily_etl, run_prices_etl 等）と ETLResult
  - etl.py : ETLResult の再エクスポートインターフェース
  - news_collector.py : RSS フィード取得・前処理・raw_news への保存ロジック
  - calendar_management.py : 市場カレンダー管理・営業日判定・夜間更新ジョブ
  - quality.py : データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査（signal/order/execution）スキーマ作成・初期化ユーティリティ

- src/kabusys/research/
  - factor_research.py : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリ、ランク関数
  - __init__.py : 研究用関数の再エクスポート

- src/kabusys/ai/__init__.py
  - ai モジュールの公開関数の再エクスポート（score_news 等）

---

## 運用上の注意・ベストプラクティス

- 環境ごとに DUCKDB のパスや API キーなどを分けた .env を用意してください（.env.local で上書き可能）。
- OpenAI のコスト・レイテンシを考慮してバッチサイズや頻度は業務要件に合わせて調整してください（news_nlp はバッチ処理を行います）。
- J-Quants の API レート制限（120 req/min）を守るため jquants_client 内でレート制御がありますが、大量の並列処理は避けてください。
- 監査（audit）テーブルは削除せず永続的に保存する運用を想定しています。
- テストでは環境変数の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、settings の差し替えやモックを行ってください。

---

必要に応じて README を拡張してサンプルワークフロー、運用チェックリスト、モニタリング（Prometheus / ログ収集）の統合方法などを追加できます。追加したい内容があれば教えてください。
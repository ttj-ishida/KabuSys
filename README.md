# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API からのデータ収集（ETL）、ニュース収集・LLM によるセンチメント評価、マーケットレジーム判定、ファクター計算・研究ユーティリティ、監査ログ用スキーマなどを提供します。内部データは主に DuckDB に保存され、OpenAI（gpt-4o-mini など）を用いた NLP 処理を行います。

---

## 主な特徴（抜粋）

- データ ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分更新・バックフィル・トークン自動リフレッシュ・レート制御（120 req/min）
- データ品質
  - 欠損、重複、スパイク、日付不整合などの品質チェック機能
- ニュース収集 & 前処理
  - RSS フィード取得（SSRF 対策／リダイレクト検証／トラッキングパラメータ削除）
  - raw_news テーブルへの冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げてセンチメント（ai_scores）を書き込み
  - レート制限・429/ネットワークエラー/5xx のリトライ処理・レスポンス検証
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して daily レジーム判定
  - LLM 呼び出しのフォールバックやリトライ管理有り
- 研究ユーティリティ
  - モメンタム、ボラティリティ、バリュー系ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions といった監査テーブル定義と初期化関数

---

## 前提・推奨環境

- Python 3.10+
- 必要なライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等も使用）

実際の依存はプロジェクトの requirements.txt / pyproject.toml を確認してください。

---

## セットアップ

1. リポジトリをチェックアウト（またはパッケージをクローン）
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージを editable インストールする場合）
     - pip install -e .

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト時等に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（例）:

     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション（オプション）
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # OpenAI
     OPENAI_API_KEY=sk-...

     # LINE 通知（任意）
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...

     # DB / ファイルパス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境 / ログレベル
     KABUSYS_ENV=development    # development|paper_trading|live
     LOG_LEVEL=INFO
     ```

   - 必須: JQUANTS_REFRESH_TOKEN（ETL 用）、OPENAI_API_KEY（ニュース NLP / レジーム判定を使う場合）

---

## 使い方（代表的な例）

以下は Python スクリプトまたは対話環境での利用例です。設定は settings オブジェクト経由で取得できます。

- 共通セットアップ例

```python
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# Conn を用意
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores テーブルに書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム判定（regime を market_regime テーブルへ保存）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って order_requests などを参照・記録できます
```

- 研究用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{'date': ..., 'code': 'xxxx', 'mom_1m': ..., ...}, ...]
```

注意:
- OpenAI の呼び出しは API コストが発生します。API キーは漏洩させないように管理してください。
- ETL / ニュース NLP / レジーム判定はいずれも「ルックアヘッドバイアス」を避ける設計がされています（target_date を渡し datetime.today() を直接参照しない等）。

---

## 環境変数一覧（主要）

- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須 for ETL）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジームで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視など）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視・プロセス制御用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（運用モード）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に実装されています。主要ファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env ロード・設定管理（settings）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py              # ニュースセンチメント（OpenAI）→ ai_scores 書き込み
  - regime_detector.py       # マーケットレジーム判定（ma200 + マクロセンチメント）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py        # J-Quants API クライアント（取得・保存・レート制御）
  - pipeline.py              # ETL パイプライン（run_daily_etl 等）
  - etl.py                   # ETLResult の再エクスポート
  - calendar_management.py   # 市場カレンダー管理・営業日判定
  - news_collector.py        # RSS 取得・前処理・保存ユーティリティ（SSRF 対策等）
  - quality.py               # データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py                 # zscore 正規化などの統計ユーティリティ
  - audit.py                 # 監査ログスキーマ初期化（signal/order/execution）
- src/kabusys/research/
  - __init__.py
  - factor_research.py       # Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py   # 将来リターン、IC、統計サマリー、rank 等

※ パッケージの __all__ に "strategy", "execution", "monitoring" が含まれているため、上記以外に戦略・実行・監視関連のモジュールが別途存在する場合があります（今回の抜粋には含まれていません）。

---

## 運用上の注意

- OpenAI の利用はコストが発生します。API キーの権限・請求を把握した上で実行してください。
- J-Quants API のレート制限（120 req/min）に従うよう設計されていますが、運用中の外部条件によっては追加のレート制御やスロットリングが必要になることがあります。
- データベース（DuckDB）のファイルパスは settings.duckdb_path で変更できます。バックアップやファイルロックに注意してください。
- 本ライブラリはバックテストや実運用用途を想定していますが、実際に発注を行うモジュール（証券会社 API 経由の発注処理）は十分な検証と安全対策（冪等、監査ログ、ポジション管理、リスク制御）を行った上で利用してください。

---

## 開発・テストのヒント

- 自動 .env 読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利です）。
- OpenAI 呼び出しや外部 HTTP 呼び出しは各モジュールでテスト用に差し替えられるよう設計されています（例: unittest.mock.patch を用いて _call_openai_api / _urlopen などをモック）。
- DuckDB はインメモリ（":memory:"）でも使えるためユニットテストでの初期化が容易です（audit.init_audit_db(":memory:") など）。

---

この README はコードベース（src/kabusys）からの抜粋を元に作成しています。実行・導入の際はプロジェクトの pyproject.toml / requirements.txt / .env.example を合わせて確認してください。質問や追加の操作例が必要であれば教えてください。
# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集・品質チェック・ニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ管理などを行うことを目的としています。

主に DuckDB をデータストアとして利用し、ETL パイプラインや研究（research）用のユーティリティ、実運用で必要となる監査テーブルを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数 / 設定
- 使い方（簡単な例）
- ディレクトリ構成
- 開発・テスト時の注意点

---

プロジェクト概要
- 日本株を対象としたデータ取得（J-Quants）、ニュース収集（RSS）、ニュースの NLP（OpenAI）によるセンチメント計測、
  市場レジーム判定、ファクター計算、ETL 管理、データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）を行うライブラリ群。
- バックテストや研究用途、運用（監視・発注）に繋げられる設計方針を持つ（ルックアヘッドバイアス回避・冪等性・フェイルセーフ等を意識）。

---

機能一覧
- 設定管理
  - .env / .env.local / 環境変数から設定を読み込み（自動読み込み・優先度あり）。
- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価（日足）・財務データ・市場カレンダーを差分取得・保存。
  - run_daily_etl を始めとするジョブ関数を提供。
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）、ページネーション、レート制御、リトライ、DuckDB への冪等保存関数。
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、ID 生成（URL 正規化 + SHA256 部分）、前処理、raw_news への保存支援。SSRF 対策やサイズ上限など安全機構あり。
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などのチェック関数と QualityIssue 型を提供。
- 市場カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、calendar の夜間更新ジョブ等。
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義、初期化関数（init_audit_schema / init_audit_db）を提供。
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコアリング（ai_scores へ書き込み）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM スコア（30%）を合成して market_regime に書き込み。
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum, value, volatility）、forward returns、IC 計算、統計サマリー、Z スコア正規化。

---

セットアップ手順（開発 / 実行環境）
1. Python バージョン
   - 本プロジェクトは Python 3.10 以降を想定しています（型ヒントで `X | None` を使用）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無ければ最低限次のパッケージを入れてください:
     - pip install duckdb openai defusedxml
   - 実運用・開発ではロギングや追加ユーティリティ等のパッケージが必要になることがあります。

4. パッケージをインストール（任意）
   - 開発時: pip install -e .
   - あるいは直接 PYTHONPATH に src を通す方法でも利用可能です。

5. 環境変数（.env）準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

主な環境変数（主な用途とデフォルト）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視関連

例（.env）
- JQUANTS_REFRESH_TOKEN=xxxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=yourpassword
- KABUSYS_ENV=development
- LOG_LEVEL=DEBUG

注意: config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動読み込みします。CI/テスト等で自動ロードを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

使い方（簡単なコード例）
※ すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を引数に取ることが多いです。

1) 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb 接続
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

4) 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
norm = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

Mock / テストに関する補足
- OpenAI API 呼び出し点（news_nlp._call_openai_api, regime_detector._call_openai_api 等）はテストでパッチ可能に設計されています。ユニットテストではこれらをモックして deterministic な挙動でテストしてください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント計算・ai_scores 書き込み
    - regime_detector.py           — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント, 保存関数
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - etl.py                       — ETL 型の再エクスポート
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS 取得・前処理・保存支援
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査テーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py           — momentum/value/volatility 等
    - feature_exploration.py       — forward returns, IC, summary, rank
  - monitoring/ (コードベース内で監視関連設定が参照される想定)
  - execution/ (発注関連の実装が入る想定)
  - strategy/ (戦略実装エントリが入る想定)

ファイルごとの詳細はソースコメント（docstring）をご参照ください。多くの関数に設計方針・フェイルセーフ・ルックアヘッドバイアス回避等の注記が含まれています。

---

開発・運用時の注意点
- Look-ahead バイアス対策:
  - AI スコアやファクター計算、ETL の多くは target_date を明示的に受け取り、内部で date.today() を参照しない設計です。バックテスト時は適切に target_date を渡してください。
- 冪等性:
  - J-Quants → DuckDB の保存関数は ON CONFLICT DO UPDATE を使い冪等化しています。
- OpenAI 呼び出し:
  - レスポンスのパース失敗や API エラー時にフェイルセーフ（デフォルトスコア 0.0）で継続する実装が多くあります。実運用ではログ監視や通知を組み合わせることを推奨します。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）や XML の安全パーサ（defusedxml）を使っています。RSS ソースは信頼できるものに限定してください。

---

貢献 / 拡張のヒント
- 発注実装（execution）や監視（monitoring）を追加して実運用ワークフローを完成させる。
- OpenAI 呼び出しに対してメトリクス（API 使用量や応答時間）を収集してレート制御を改善する。
- ETL の並列化や分页戦略を改良して大規模データ取得を高速化する。
- unit / integration テストを整備する。API 呼び出しはモックや VCR 的な再生を活用。

---

本 README はコードベースの主要機能・基本的な使い方をまとめたものです。さらに詳しい仕様や設計文書（例: DataPlatform.md, StrategyModel.md）がプロジェクト内にあればそちらも参照してください。必要であれば README を拡張してサンプルスクリプトや CI 設定、デプロイ手順を追加できます。
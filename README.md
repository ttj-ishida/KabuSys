# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株を対象としたデータパイプライン、リサーチ、AI（ニュースNLP / レジーム判定）、および監査・発注追跡のための内部ライブラリ群です。本リポジトリはETL・データ品質チェック、ニュース収集、AI によるニュースセンチメント評価、ファクタ計算・特徴量解析、監査テーブル初期化など運用／研究に必要な共通機能を提供します。

主な設計指針
- ルックアヘッドバイアスを避ける（内部で date.today() 等を直接参照しない関数設計）
- DuckDB をデータ層として利用（ETL は冪等化、ON CONFLICT を使用）
- 外部APIへの呼び出しは堅牢なリトライ・レート制御を実装
- AI 呼び出しは JSON Mode を使いレスポンス検証を行う（OpenAI）
- セキュリティ配慮（ニュース収集の SSRF 対策、XML 脆弱性対策など）

---

## 主な機能一覧

- data/
  - ETL パイプライン（J-Quants から株価 / 財務 / カレンダーの差分取得）
  - jquants_client：J-Quants API クライアント（認証・ページネーション・リトライ・保存）
  - calendar_management：JPX カレンダーの管理と営業日判定ユーティリティ
  - news_collector：RSS 収集、前処理、raw_news への保存（SSRF/サイズ制限対応）
  - quality：データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit：監査用テーブル（signal_events, order_requests, executions）と初期化関数
  - stats：Zスコア正規化など汎用統計ユーティリティ
- ai/
  - news_nlp：ニュース記事をまとめて OpenAI に投げ、銘柄別センチメント（ai_scores）を作成
  - regime_detector：ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research：モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration：将来リターン、IC（Information Coefficient）、統計サマリー等
- config.py：環境変数読み込み・設定管理（.env / .env.local 自動読み込み、無効化フラグあり）
- data.audit.init_audit_db：監査用の DuckDB DB を初期化するユーティリティ

---

## 動作要件（概略）

- Python 3.10+（型注釈に Union | を使用しているため）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib、logging、datetime、json 等

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（例）
   - pip install duckdb openai defusedxml

   （パッケージやバージョンはプロジェクトの requirements.txt があればそれを使用してください）

3. パッケージを開発インストール（オプション）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動読み込みされます（config.py が .git / pyproject.toml を基準に探索）。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

例: .env (最低限必要なもの)
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意: config.Settings が必須のキーを require しているため、JQUANTS_REFRESH_TOKEN 等が未設定のときは ValueError が発生します（必要に応じてテスト時は環境変数や引数で注入してください）。

---

## 使い方（簡単な例）

下記は主要なユーティリティ関数の呼び出し例です。実運用では例外ハンドリングやロギング、スケジューラ（cron / systemd timer 等）を組み合わせてください。

1) DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を基準に実行
print(result.to_dict())
```

3) ニュースの AI スコアリング（前日15:00 JST〜当日08:30 JST の記事を処理）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数 OPENAI_API_KEY を使用
print(f"scored {n} codes")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査DB 初期化（監査用 DuckDB を新規作成して接続を受け取る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルにレコードを挿入／参照
```

6) ファクター計算・リサーチ関数
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
from datetime import date

factors = calc_momentum(conn, date(2026, 3, 20))
z_factors = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 主要設定項目（環境変数）

config.Settings で参照される主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (development | paper_trading | live, デフォ: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

注意: OpenAI API は関数引数として api_key を渡すか、環境変数 OPENAI_API_KEY を利用します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - ai/__init__.py
  - research/*

（実際のリポジトリにはテスト、scripts、ドキュメント、pyproject.toml 等が含まれる可能性があります）

---

## 注意事項 / 運用上のポイント

- Look-ahead バイアス防止:
  - 多くの関数は target_date を明示的に受け取るか、内部で DB の date < target_date 条件を使いルックアヘッドを防止しています。バックテストや再現性に注意してください。
- API レート制御:
  - J-Quants クライアントは 120 req/min の制約を考慮してスロットリングしています。過度な同時呼び出しは避けてください。
- OpenAI 呼び出し:
  - JSON Mode を使用しますが、LLMの不確実性に備えレスポンスのバリデーション（パースや型チェック）を行っています。
- news_collector:
  - RSS フィードの取得は SSRF と XML 攻撃に対する防御を備えていますが、信頼できるソースを使うことを推奨します。
- DB マイグレーション:
  - DuckDB のスキーマ管理やマイグレーションはこのリポジトリに明示的なマイグレーションフレームワークは含まれていません。スキーマ初期化・変更時は注意してください。
- テスト:
  - OpenAI / 外部ネットワーク呼び出しはモック可能な設計（内部 _call_openai_api の差替えなど）になっています。ユニットテストでは環境変数の自動読み込みを無効化すると便利です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## トラブルシューティング

- 環境変数が足りない:
  - settings プロパティは必須キーをチェックして ValueError を発生させます。ログやスタックトレースでどのキーが不足しているか確認してください。
- J-Quants API エラー:
  - 401 は自動的にリフレッシュを試行しますが、リフレッシュ失敗時はエラーになります。refresh token の有効性を確認してください。
- OpenAI レスポンスパース失敗:
  - LLM のレスポンスが不正な JSON の場合、該当チャンクはスキップして処理を継続します（フェイルセーフ）。ログを確認してプロンプトや入力データを見直してください。

---

README は以上です。必要であれば以下も提供します：
- .env.example のテンプレート
- requirements.txt の推奨パッケージ一覧
- より詳細な運用手順（cron / systemd 例、監視設定）
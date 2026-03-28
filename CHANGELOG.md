# Changelog

すべての重要な変更をここに記録します。これは Keep a Changelog の様式に従っています。  

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージメタ情報を追加（__version__ = 0.1.0）。公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理
  - src/kabusys/config.py:
    - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースを強化（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応）。
    - _load_env_file の override/protected ロジック: OS 環境変数を上書きしない安全な挙動。
    - Settings クラスを提供し、主要設定をプロパティで取得：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
      - KABUSYS_ENV の検証 (development / paper_trading / live)
      - LOG_LEVEL の検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
      - is_live / is_paper / is_dev ヘルパー

- AI: ニュースNLP と レジーム判定
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を基に銘柄別ニュースをバッチで集約し、OpenAI (gpt-4o-mini) の JSON mode を用いて銘柄ごとのセンチメント（ai_score）を計算。
    - チャンクサイズ、最大記事数・文字数トリム、バッチ処理、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等的な書き換え（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモック差替え可能。
    - calc_news_window: ターゲット日に対応するニュース収集ウィンドウ計算（JST 基準の UTC 変換を含む）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロニュースタイトルを取得。
    - OpenAI 呼び出しは独立実装。リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に API 呼び出し差替え可能な設計。

- 研究（Research）モジュール
  - src/kabusys/research/__init__.py: 主要研究ユーティリティを再エクスポート。
  - src/kabusys/research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー系ファクター計算:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（データ不足時は None 処理）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出（最新財務データの選択は report_date <= target_date）。
    - DuckDB を用いた SQL＋Python 実装で外部 API に依存しない。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定基準日からの将来リターン（任意ホライズン）を一括取得する効率的クエリ。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めによる ties の検出を考慮）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。

- データプラットフォーム
  - src/kabusys/data/calendar_management.py:
    - JPX マーケットカレンダー管理（market_calendar の読み書き、営業日判定、前後営業日取得、期間内営業日列挙、SQ 判定）。
    - DB 値優先、未登録日は曜日ベースでフォールバック。探索上限で ValueError を返す安全設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - src/kabusys/data/pipeline.py:
    - ETL パイプライン用ユーティリティ。差分取得、保存、品質チェックの設計方針を実装。
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラー集計、has_errors / has_quality_errors 等のヘルパー）。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート。

- テスト/運用を意識した設計メモ（コード内ドキュメント）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない実装方針を明記。
  - データベース書き込みは冪等性を重視（DELETE → INSERT／ON CONFLICT の利用など）。
  - API 失敗時はスキップやデフォルト値（例: macro_sentiment=0.0）で継続するフェイルセーフ設計。
  - DuckDB の executemany の互換性や空リスト制約を考慮した実装。
  - OpenAI 呼び出しはテストしやすいよう差替え可能な内部関数を用意。

### 変更 (Changed)
- 該当なし（初回リリース）。

### 修正 (Fixed)
- 該当なし（初回リリース）。

### 既知の注意点 / 使用上のメモ
- 環境変数必須項目（少なくとも実行する機能に応じて設定が必要）:
  - OPENAI_API_KEY (AI 機能を使う場合)
  - JQUANTS_REFRESH_TOKEN (J-Quants を用いる場合)
  - KABU_API_PASSWORD (kabuステーション API を使う場合)
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (Slack 通知を使う場合)
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (モニタリング用): data/monitoring.db
- OpenAI API との通信は gpt-4o-mini を想定（JSON mode 使用）。レスポンスの不完全さや余計な前後テキストに対しても復元/検証処理を実装。
- DuckDB と SQL クエリは日付を naive datetime/date として扱うことを前提としているため、実運用でのタイムゾーン取り扱いに注意。

---

今後のリリースでは、API クライアントの差替え、追加の戦略実装、モニタリング・実行モジュールの詳細実装、より詳細な品質チェックの集約などを予定しています。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]
- 今後の変更予定やマイナー修正をここに記載します。

## [0.1.0] - 2026-03-28
初回リリース。日本株用のデータ取得・分析・AIスコアリング・環境管理を目的としたツール一式を提供します。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - Settings クラスを提供し、アプリケーション設定を環境変数から取得（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。
  - .env ファイル自動ロード機能を実装（プロジェクトルート判定：.git または pyproject.toml を探索）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーを強化（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）と読み込み時のオーバーライド・保護（protected keys）機構。
  - 環境値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と便宜メソッド（is_live / is_paper / is_dev）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（記事数上限・文字数トリム）、JSON Mode 出力のバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。失敗時は個別チャンクをスキップして他銘柄の結果を保護。
    - スコアを ai_scores テーブルへ上書き（DELETE → INSERT）する冪等保存ロジック。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF（1321）の200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し market_regime に保存。
    - マクロキーワードフィルタで raw_news を抽出し、OpenAI（gpt-4o-mini）に JSON レスポンスを求める。API障害時はフェイルセーフ（macro_sentiment=0.0）。
    - DuckDB を使ったデータ取得・計算と、BEGIN/DELETE/INSERT/COMMIT を用いた冪等書き込みを実装。
    - OpenAI 呼び出しは専用ヘルパー関数を使用（テスト時に差し替え可能）。

  - 共通設計思想（AI）
    - 全 AI 系処理は日付参照で datetime.today()/date.today() を直接参照せず、target_date を明示的に与えることでルックアヘッドバイアスを排除。
    - OpenAI のレスポンス解析は堅牢化（JSON 抽出、キー検査、型検査、スコアのクリップなど）。

- データモジュール（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を公開（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新・バックフィル・品質チェックの指針を実装するユーティリティ（テーブル存在確認、最大日付取得、トレーディング日調整等）。
    - J-Quants クライアント（jquants_client）との連携を前提に設計。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を前提に営業日判定・前後営業日探索・期間内営業日取得を実装（DB 登録優先、未登録日は曜日ベースでフォールバック）。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを含む）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループを回避。

  - ETL インターフェース再エクスポート（src/kabusys/data/etl.py）
    - pipeline.ETLResult を外部に公開。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比率）、PER/ROE の計算関数を実装。
    - DuckDB 内で SQL を使って効率的に計算。データ不足時は None を返す設計。
    - 出力は (date, code) をキーとした辞書リスト形式。

  - 特徴量探索・統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）。複数ホライズンを一度に取得するクエリ実装、ホライズン検証。
    - IC（Information Coefficient）計算（Spearman の ρ）とランク付けユーティリティ（rank）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）の算出。
    - kabusys.data.stats.zscore_normalize の再エクスポートを提供。

- 共通ユーティリティ
  - DuckDB を前提とした SQL 実行・日付変換ユーティリティ（_to_date 等）。
  - 各種モジュールでのログ出力と例外処理の一貫化（ロールバック処理・ログの残し方など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して誤使用を防止。

### Notes / Design decisions
- ルックアヘッドバイアス対策として、全ての「日付基準」関数は外部から target_date を与える形で実装し、内部で現在日時を参照しない設計になっています。
- DB 書き込みは冪等化を重視（DELETE→INSERT、ON CONFLICT 想定、トランザクションとロールバック）。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を前提にしつつ、現実のレスポンス欠陥に備えてパース復元処理を実装しています。
- ETL/データ取得は「差分取得＋バックフィル」で後出し修正を吸収する方針です。
- 外部依存は最小化（標準ライブラリ + duckdb + openai）。Pandas 等は使用していません（研究モジュールも標準ライブラリで完結）。

---

過去バージョン履歴はこのファイルから始まります。次回以降の変更では Unreleased 欄に修正を記載し、リリース時に日付とバージョンを付けて移動してください。
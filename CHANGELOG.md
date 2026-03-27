# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [Unreleased]
- なし（初回公開は 0.1.0）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装・公開。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にて公開。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して特定（CWD非依存）。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォートやエスケープ、インラインコメント扱いなどに対応。
  - .env 読み込み時の上書き制御（override フラグ）と protected（OS 環境変数保護）機能。
  - Settings クラスで主要設定をプロパティ提供（J-Quants トークン、kabu API、Slack トークン/チャネル、DB パス、環境種別、ログレベル等）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 値チェック。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄単位にテキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたり記事数上限・文字数上限でトリム（トークン肥大対策）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score 検証、数値チェック、既知コードのみ採用）。
    - スコアは ±1.0 にクリップ。成功時は ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗対策）。
    - テスト向けに内部の OpenAI 呼び出し関数を patch 可能に実装。
    - 時間ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して DB と照合。

  - レジーム検出（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム判定（bull / neutral / bear）を算出。
    - prices_daily から ma200_ratio を算出（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）。データ不足時は中立（1.0）を採用。
    - raw_news からマクロキーワードでフィルタしてタイトルを収集し、OpenAI により macro_sentiment を取得（記事がない場合は LLM 呼び出しせず 0.0）。
    - OpenAI コールはリトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を採用。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックして例外を伝播。

- データプラットフォーム（src/kabusys/data）
  - ETL/パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（ETL 実行結果・メトリクス・品質問題・エラーの収集）。
    - 差分取得、保存（jquants_client の idempotent 保存を想定）、品質チェックの枠組みを実装。
    - backfill による過去数日の再取得、品質チェックは Fail-Fast にしない設計。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの存在確認と夜間バッチ更新 job を実装（calendar_update_job）。
    - J-Quants から差分取得し ON CONFLICT DO UPDATE 相当で保存（jq.fetch_market_calendar / jq.save_market_calendar を使用）。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダー情報がない場合は曜日ベース（平日）でフォールバックする設計。
    - 最大探索日数・バックフィル日数・健全性チェックを組み込み（例: 最大探索 _MAX_SEARCH_DAYS）。
  - jquants_client 参照を前提としており、ETL や calendar job から利用する設計。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（欠損条件に配慮）。
    - Value: raw_financials から最新財務情報を取得し PER / ROE を計算。
    - DuckDB の SQL を多用して処理（prices_daily / raw_financials のみ参照）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）、IC（Spearman rank）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を提供。
    - 外部依存を持たない純粋 Python 実装（pandas 等未使用）。
    - 入出力は dict/list ベースで、テスト・パイプライン組込みを想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Design / 安全策（注記）
- ルックアヘッドバイアス回避: 各 AI / 研究モジュールは datetime.today() / date.today() を直接参照せず、必ず caller から target_date を受け取る設計。
- OpenAI 呼び出しの堅牢性:
  - レートリミット・ネットワーク・タイムアウト・5xx エラーに対する再試行とフォールバック（デフォルトでゼロや空スコアを返す）。
  - テスト時に内部 API 呼び出しをモックできるよう分離実装。
- DB 書き込みの冪等性を考慮:
  - ai_scores や market_regime 等は置換（DELETE → INSERT）で書き込むことで再実行の安全性を確保。
  - DuckDB の executemany に対する互換性配慮（空リストを渡さないチェック等）。
- .env パーサは実運用の多様なフォーマット（export, quoted values, inline comments）に対応。

### Known limitations / TODO（実装から推測）
- 一部外部モジュール（jquants_client, quality 等）は実体を参照しており、実行にはそれらの実装や適切な DB スキーマが必要。
- 現フェーズでは PBR・配当利回り等のバリューファクターは未実装（calc_value の注記参照）。
- モデルやプロンプト設計、バッチサイズ・トークン管理等は今後チューニングの余地あり。

---

（注）本 CHANGELOG は提供されたソースコードの構成・コメント・実装内容から推測して作成しています。実際のリリースノートとして公開する前に、プロジェクトのリリースポリシーやドキュメントと照合してください。
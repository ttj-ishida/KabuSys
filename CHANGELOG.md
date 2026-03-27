# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初回リリースに関する実装内容・設計方針・公開 API をコードベースから推測して日本語でまとめています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 環境設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート自動検出 .git / pyproject.toml 基準）。
  - .env の詳細パース実装（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントなど対応）。
  - 自動ロードの無効化環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数必須チェック用 _require、Settings クラスの公開（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定プロパティ）。
  - 一部設定のバリデーション（KABUSYS_ENV / LOG_LEVEL）。

- AI 関連モジュール（kabusys.ai）を追加。
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429, ネットワーク, タイムアウト, 5xx に対して指数バックオフ）、レスポンスバリデーション、スコアの ±1 クリップ。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 対象に想定）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）。
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news / market_regime を参照して計算・冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは個別実装でモジュール結合を低く保ち、API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。
    - エラー・リトライ戦略、JSON パース保険、ログ出力を実装。

- Data / ETL / Calendar / Pipeline（kabusys.data）を追加。
  - マーケットカレンダー管理（data.calendar_management）。
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した設計。
    - カレンダー夜間更新ジョブ calendar_update_job（J-Quants から差分取得・バックフィル・健全性チェック・冪等保存）。
  - ETL パイプラインインターフェース（data.etl / data.pipeline）。
    - ETLResult データクラスを公開して ETL 実行結果（取得数/保存数/品質チェック/エラー）を表現。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - DuckDB をデータストアとして想定したユーティリティ関数（テーブル存在チェック、最大日付取得など）。
  - jquants_client との連携を想定（fetch/save のラッパ利用）。

- 研究（Research）モジュール（kabusys.research）を追加。
  - ファクター計算（research.factor_research）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）を計算する関数を提供（calc_momentum, calc_value, calc_volatility）。
    - DuckDB 上で SQL を用いた効率的計算、データ不足時の None 戻し、結果を辞書リストで返却。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、可変ホライズン、ホライズンバリデーション）。
    - IC（Information Coefficient）計算（calc_ic、スピアマンランク相関）。
    - ランク変換ユーティリティ（rank）。
    - 統計サマリー（factor_summary：count/mean/std/min/max/median 計算）。
  - 研究用ユーティリティとして zscore_normalize を data.stats から再エクスポート。

- パブリック API の整理
  - ai: score_news(conn, target_date, api_key=None) → ai_scores テーブルへ書き込み
  - ai: score_regime(conn, target_date, api_key=None) → market_regime へ書き込み
  - research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - data: calendar_update_job, is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - config: settings（Settings インスタンス）を公開

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 自動読み込みで OS 環境変数が保護されるよう設計（.env 読み込み時の protected set）。  
- OpenAI API キーの利用は引数注入または OPENAI_API_KEY 環境変数で行い、キー未指定時は明示的な ValueError を送出して誤用を防止。

### Design / Implementation Notes（重要な設計方針）
- ルックアヘッドバイアス防止のため、date / target_date を明示的に受け取り内部で datetime.today() / date.today() を直接参照しない実装を徹底。
- DuckDB を主なローカル分析 DB として想定。SQL と Python を組み合わせて効率的に集計・窓関数を利用。
- LLM 呼び出しはフェイルセーフ（API 失敗時は 0.0 にフォールバック、例外は上位に伝播しない）かつリトライ設計（指数バックオフ）を採用。
- テスト容易性を考慮し、OpenAI 呼び出し箇所は内部関数を patch することで差し替え可能に設計。
- DuckDB の executemany の制約（空リスト不可）に対応するガードを追加。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 等）して部分失敗時のデータ保護を優先。

### Required environment variables
- JQUANTS_REFRESH_TOKEN（J-Quants API 用）
- KABU_API_PASSWORD（kabu ステーション API 用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用 Slack）
- OPENAI_API_KEY（AI モジュールを利用する際に必要。関数呼び出しで api_key を渡すことも可能）
- その他オプション: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD

---

注記:
- ここに記載した内容はコードベースから推測した実装・設計・公開 API の要約です。実際の運用や API 仕様は README / ドキュメントを参照してください。
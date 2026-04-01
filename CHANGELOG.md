Keep a Changelog
================

この CHANGELOG は Keep a Changelog の書式に準拠しています。  
リリース日付はコードベースの作成日・推定日を基に記載しています（推測に基づくため実際のリリース日とは異なる場合があります）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-01
--------------------

追加 (Added)
- パッケージ初期実装を追加
  - kabusys パッケージの公開モジュール群（data, strategy, execution, monitoring）をエクスポートするパッケージ初期化。
- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートは .git または pyproject.toml から解決）。
  - export KEY=val 形式やクォート、インラインコメントを考慮したパーサー実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 必須環境変数取得のヘルパー（_require）と Settings クラス実装（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境等のプロパティ）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev ユーティリティ。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON モード）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事・文字数トリムの実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ実装。
    - レスポンスの厳格なバリデーション、スコアの ±1.0 クリップ、部分成功時の安全な DB 書込み（該当コードのみ DELETE→INSERT）。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime を日次判定。
    - OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 でフォールバックするフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。
- データ（Data）モジュール (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日ロジックを提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job による J-Quants からの差分取得→冪等保存（バックフィル/健全性チェック含む）。
  - ETL パイプライン補助（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスによる ETL 実行結果の集約（品質チェック結果とエラー集計を含む）。
    - 差分更新、バックフィル、品質検査のためのユーティリティ（jquants_client / quality に依存）。
    - DuckDB 周りの互換性考慮（executemany の空リスト制約等）に配慮した実装。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金／出来高比率）を DuckDB SQL で計算。
    - データ不足時の None ハンドリング、日付ウィンドウのバッファ設計。
    - 公開関数: calc_momentum, calc_value, calc_volatility。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
- ロギング / 安全設計
  - 各所に logger を配置し、API エラーやデータ不足時に警告／情報ログを出力。
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（target_date ベース）。
  - DuckDB に対する冪等操作（DELETE→INSERT など）やトランザクション制御（BEGIN/COMMIT/ROLLBACK）を導入。
- テスト支援
  - OpenAI 呼び出し部をモック可能にしてユニットテスト容易化（関数単位で差し替え可能）。

変更 (Changed)
- 初期リリースのため該当なし（新規追加のみ）。

修正 (Fixed)
- 初期リリースのため該当なし。

既知の制限 (Known issues / Notes)
- OpenAI API の利用には OPENAI_API_KEY が必要（score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照）。
- .env の自動ロードはプロジェクトルートが特定できる場合のみ動作。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化推奨。
- DuckDB のバージョン依存で executemany に空リストを渡せない点を回避する実装がある（互換性に注意）。
- news_nlp と regime_detector は OpenAI の JSON mode に依存。LLM レスポンスのフォーマット不整合はフェイルセーフでスキップまたは 0.0 にフォールバックする。
- 一部機能（strategy / execution / monitoring）の具象実装はこのリリース範囲外（パッケージ構成上は公開予定の名前空間あり）。

移行・導入メモ (Migration / Setup)
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings クラス参照）。
- デフォルト DB パス:
  - DUCKDB_PATH= data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH= data/monitoring.db（デフォルト）
- 監視用 PID / リソース閾値のデフォルトも Settings に定義されているため .env で上書き可能。
- DuckDB 接続に渡すテーブルスキーマはコードコメント内の期待形に合わせて準備すること（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）。

セキュリティ (Security)
- 環境変数ベースの機密情報（API キー等）は .env ファイル／環境変数で管理。自動読み込み時に存在する OS 環境変数は保護され、.env.local は上書き可能。

貢献 (Contributing)
- 初期リリースのため貢献ガイドラインは別途ドキュメント化を推奨。

--- 

注記: 本 CHANGELOG は提供されたソースコード内容からの推測に基づいて作成しています。実際の変更履歴やリリースノートが存在する場合はそちらを優先してください。
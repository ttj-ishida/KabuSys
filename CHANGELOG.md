# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリースポリシー: semver 準拠。

## [Unreleased]

（未リリースの変更なし）

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームのコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - パッケージ名: kabusys。トップレベル __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - パッケージ配布後でも動作するよう、__file__ を起点にプロジェクトルート（.git または pyproject.toml）を自動検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス、クォート文字内のバックスラッシュエスケープ、行内コメント判定等に対応。
  - 環境変数上書きの保護機能（protected set）を実装し OS 環境変数を保護。
  - Settings クラスを追加しアプリケーション設定をプロパティ経由で提供。
    - J-Quants / kabuステーション / Slack / DB パス等の設定を提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。
    - 必須環境変数未設定時は明確な ValueError を送出。

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.py)
    - raw_news と news_symbols を集約して銘柄別にニュースを整形し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチ処理（1 API コールあたり最大 _BATCH_SIZE=20 銘柄）・記事数/文字数トリム・JSON mode による厳密なレスポンス取得。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（results 配列、code/score の検証、スコアの有限性チェック）を実装。
    - ai_scores テーブルへ冪等的に DELETE → INSERT で書き込み（部分失敗時に既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出し箇所は関数化されておりモック差し替え可能。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily market regime（bull/neutral/bear）を算出。
    - ma200_ratio の計算は target_date 未満のデータのみを参照してルックアヘッドを防止。
    - マクロニュース取得は news_nlp の time window 計算を利用し、タイトルを LLM へ渡して macro_sentiment を算出。
    - API 失敗時は macro_sentiment = 0.0 とするフェイルセーフ挙動。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時は ROLLBACK を試行。

- 研究（Research）モジュール (src/kabusys/research)
  - factor_research.py: ファクター計算機能を実装
    - Momentum: mom_1m, mom_3m, mom_6m（約1/3/6ヶ月）、ma200_dev（200日移動平均乖離率）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高変化率。
    - Value: per, roe（raw_financials と prices_daily を組合せて計算）。
    - 実装は DuckDB 上で SQL を用いて行い、データ不足時は None を返す設計。
  - feature_exploration.py: 特徴量評価ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を実装。必要な有効レコード数が不足する場合は None を返す。
    - rank: 同順位は平均ランクとするランク化ロジック（浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- データプラットフォーム（Data）モジュール (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末判定）で一貫性を保つ実装。
    - calendar_update_job を実装し J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）・健全性チェックを行う。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得・保存（jquants_client 経由の idempotent 保存）・品質チェック（quality モジュール）を想定した骨組みを実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、market calendar 調整ヘルパー等。
    - ETLResult.to_dict は quality_issues をシリアライズ可能な形に変換。

- 共通
  - DuckDB を中心に設計（duckdb.DuckDBPyConnection を多数受け取る関数群）。
  - ログ出力（logging）を活用し処理の経過や警告を明確に記録。
  - API キー注入可能な設計（関数引数で api_key を渡せ、テスト時に差し替えやすい）。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照しない設計方針を各所で一貫適用（target_date ベース）。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- OpenAI API キーや各種トークンは環境変数経由で管理。必須環境変数が未設定の場合、明示的なエラーを発生させることで意図しない挙動を防止。

### 互換性 / マイグレーションノート (Migration)

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（各処理で必須とされる）
- .env 自動読み込みはパッケージルート（.git または pyproject.toml）を基準に行われます。CI 等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース: デフォルトで DuckDB/SQLite のパスを data/ 配下に想定しています（DUCKDB_PATH, SQLITE_PATH により変更可）。
- DuckDB バインド挙動に依存する箇所があるため、DuckDB のバージョン互換性に注意してください（executemany に空リストを渡さない等のワークアラウンドを実装）。

---

今後の予定（非網羅）:
- strategy / execution / monitoring の実装拡張（発注ロジック、実行監視、Slack 通知等）。
- テストカバレッジ強化と CI 設定。
- J-Quants / kabu API クライアントの詳細実装と API エラー処理の強化。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。理解しやすさのため日本語で記載します。

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開します。データ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュース NLP／LLM 統合、マーケットレジーム判定など、研究・運用に必要な基盤を含みます。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定読み込みを行う自動ローダーを実装（プロジェクトルート検出は .git または pyproject.toml 基準）。
  - .env パーシング実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリで使用する各種必須/任意設定値をプロパティで参照可能に実装（J-Quants / kabuステーション / Slack / DB パス / 環境設定など）。
  - 設定値検証: KABUSYS_ENV, LOG_LEVEL の許容値チェックおよび is_live/is_paper/is_dev のユーティリティ。

- ニュース NLP（LLM）スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news テーブルと news_symbols を入力に、銘柄ごとのニュースセンチメント（ai_score）を OpenAI（gpt-4o-mini）で算出し ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当の UTC 範囲）を提供（calc_news_window）。
  - バッチ化（最大 20 銘柄／コール）、記事トリミング、スコアクリップ（±1.0）、レスポンスバリデーションを実装。
  - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。パース失敗や API エラー時は当該チャンクをスキップして続行。
  - DuckDB の executemany の挙動差異に配慮して、DELETE/INSERT は個別パラメータ実行（空リストを避けるガードあり）。
  - テストのしやすさを考慮し、API 呼び出し部分は _call_openai_api の差し替え（unittest.mock.patch）でモック可能。

- マーケットレジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する機能を実装。
  - prices_daily と raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
  - LLM 呼び出しでのリトライ、API 失敗時は macro_sentiment = 0.0 のフェイルセーフを採用。
  - 内部ではルックアヘッドバイアスを防ぐ設計（datetime.today() を参照しない・クエリは date < target_date 等で排他）。

- データプラットフォーム（Data）モジュール
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存 → バックフィル・健全性チェック）。
  - ETL パイプラインインターフェース (src/kabusys/data/etl.py / pipeline.py)
    - ETLResult データクラスを実装し ETL 実行結果の構造化を提供。
    - 差分更新、バックフィル、品質チェックのためのユーティリティ（内部関数や DB 最大日付取得等）を実装。
    - jquants_client および quality モジュールと連携する設計。

- リサーチ（研究）モジュール (src/kabusys/research/)
  - factor_research.py: Momentum、Value、Volatility（ATR, 平均売買代金等）などのファクター計算を実装（prices_daily / raw_financials を参照）。
  - feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（スピアマン）計算、rank、統計サマリー機能を実装（外部ライブラリ不使用）。
  - data.stats の zscore_normalize を re-export。

- その他
  - AI/News と Regime モジュールは OpenAI API の gpt-4o-mini を利用する設計（JSON Mode を利用した厳密な JSON 応答期待）。
  - ロギングによる詳細情報出力と各種警告処理を充実させ、フェイルセーフの挙動を明示。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 廃止 (Deprecated)
- 初回公開のため該当なし。

### 削除 (Removed)
- 初回公開のため該当なし。

### セキュリティ (Security)
- 初回公開のため該当なし。

---

## 重要な運用・移行情報（Usage / Notes）

- 環境変数
  - 必須:
    - OPENAI_API_KEY（news_nlp / regime_detector の API 呼び出しに使用、関数引数で上書き可）
    - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）
    - KABU_API_PASSWORD（Settings.kabu_api_password）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知用）
  - 任意（デフォルトあり）:
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
    - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
  - 自動 .env 読み込み
    - プロジェクトルートにある .env と .env.local を自動読み込み（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- DB テーブル（DuckDB）要件（モジュール利用時）
  - news_nlp: raw_news, news_symbols, ai_scores
  - regime_detector: prices_daily, raw_news, market_regime
  - research modules: prices_daily, raw_financials（ファクター計算に必要）
  - calendar_management: market_calendar（未取得時は曜日ベースでフォールバック）
  - ETL / pipeline: ETLResult を利用する処理や jquants_client / quality と併用

- LLM / API の挙動
  - gpt-4o-mini を想定した JSON Mode を利用（厳密な JSON を期待）。ただし、レスポンスに前後テキストが混入する場合の復元ロジックを実装。
  - API 呼び出しは再試行ロジックを備え、失敗時は安全にフォールバック（例: macro_sentiment=0.0、チャンクスキップ）するため、LLM の一時障害でシステム全体が停止しない設計。
  - テスト時は _call_openai_api をモックすることで API 呼び出しを差し替え可能。

- テスト時の注意点
  - DuckDB の executemany に関する互換性のため、空パラメータリストを渡さない実装（空リストの場合は実行をスキップ）を行っています。古い DuckDB バージョンを使用する場合は互換性に注意。

- 設計方針の明示
  - ルックアヘッドバイアス回避のため、どのモジュールも datetime.today()/date.today() を直接使わず、呼び出し側から target_date を渡す API 設計を採用しています。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT による上書き）にし、部分失敗時に既存データを保護する実装です。

---

フィードバックや不具合報告、追加してほしい機能があればお知らせください。次回リリースではドキュメント強化、CLI/API のサンプル、テストカバレッジの拡充を予定しています。
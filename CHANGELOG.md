# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 日付は本リリース作成日です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・データ基盤・リサーチ・AI 支援処理の基礎機能を実装しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）し、主要サブパッケージ（data, research, ai, ...）を公開。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定
  - 環境変数 / .env 管理モジュール（kabusys.config）を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パーサーは quote やエスケープ、コメントの扱いに対応。
    - _load_env_file で OS 側既存環境変数を保護する protected 機能を実装。
  - Settings クラスを提供（型検証・必須チェック・デフォルト値を含む）。
    - J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル判定プロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、銘柄内記事トリム（文字数・記事数上限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスバリデーションとスコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等（DELETE → INSERT）書き込み。部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - calc_news_window を利用した時間ウィンドウ、マクロキーワードフィルタ、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - API エラー時のフェイルセーフ（macro_sentiment = 0.0）とリトライ処理。
    - テスト用に _call_openai_api を差し替え可能。

- データ基盤（DataPlatform）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック（週末は非営業日扱い）。
    - calendar_update_job により J-Quants から差分取得・冪等保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン基礎（kabusys.data.pipeline, etl）
    - ETLResult データクラスで実行結果を集約（取得数/保存数/品質問題/エラー）。
    - 差分更新・バックフィル戦略、品質チェック呼び出しのインフラを準備。
    - jquants_client 経由での取得 / 保存連携を想定した設計。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB クエリベースで実装。
    - データ不足時は None を返す安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman）計算 calc_ic、ランク変換、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存無しで実装。
  - zscore_normalize を data.stats から再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （現時点で特記するセキュリティ修正は無し）
  - 注意: OpenAI / J-Quants / Slack 等の API キーは環境変数で管理する必要があります（Settings で必須チェック）。

### Notes / 実装上の設計判断・注意点
- ルックアヘッドバイアス防止:
  - AI スコア算出・レジーム判定・ETL 等で datetime.today()/date.today() を直接参照しないよう設計。すべて明示的な target_date を受け取り、DB クエリは target_date 未満／未満等で過去データのみを参照します。
- フェイルセーフ:
  - OpenAI 呼び出しが失敗しても全体処理を停止させずフォールバック（0.0 またはスキップ）して続行する設計。
- テスト容易性:
  - OpenAI 呼び出しラッパー（_call_openai_api）を patch 可能にしてユニットテストで差し替えられるようにしました。
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- DuckDB 互換性:
  - executemany に空リストを渡せない等の既知制約を考慮して実装（空チェックを行う）。

既知の要件:
- 動作には DuckDB、OpenAI SDK、J-Quants クライアント（kabusys.data.jquants_client を想定）などの依存が必要です。
- 実行前に必要な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を設定してください。

---

今後の予定（例）:
- 0.2.x: 発注 / 実行エンジン（kabu ステーション連携）とモニタリングの実装、追加ユニットテストと E2E テスト整備。
- AI モデルの選択肢・プロンプト改良、レスポンス検証の強化。
- jquants_client や quality モジュールの実装・統合テスト。

（以上）
CHANGELOG.md
=============

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠しています。  
リリース履歴はコードベース（src/kabusys）から推測して作成しています。

※ 日付・文言はソースコード内のバージョン / コメントや設計方針から推測したものです。

Unreleased
----------

- なし

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - 高レベル概要
    - 日本株自動売買システムの基盤ライブラリを提供。
    - モジュール構成: data, research, ai, config, research 内の各種分析ユーティリティ等を公開。

  - 環境設定・ロード
    - 環境変数 / .env ファイル読み込みユーティリティを実装（kabusys.config）。
      - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト等向け）。
      - export KEY=val、シングル/ダブルクォート、インラインコメントなどを考慮した .env パーサーを実装。
      - 必須環境変数取得時に未設定なら ValueError を投げる _require ユーティリティを提供。
      - 公開設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等、Slack/DBのパスや実行環境フラグ（KABUSYS_ENV, LOG_LEVEL）を取得する Settings クラス。

  - データプラットフォーム（data）
    - ETL パイプラインのインターフェースと結果型を実装（kabusys.data.pipeline.ETLResult, kabusys.data.etl 再エクスポート）。
      - 差分更新、バックフィル、品質チェックの設計方針を実装。
      - DuckDB を想定したテーブル存在チェックや最大日付取得などのユーティリティを提供。
    - カレンダー管理（kabusys.data.calendar_management）
      - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）。
      - 営業日判定・前後営業日取得・期間内営業日取得・SQ判定等の API を提供。
      - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
      - 最大探索幅や健全性チェックを組み込み、極端なケースでの無限ループや誤動作を防止。

  - 研究 / ファクター群（research）
    - ファクター計算（kabusys.research.factor_research）
      - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高比率）を DuckDB クエリベースで実装。
      - データ不足時の None 処理やログ、スキャン範囲バッファ等を実装。
    - 特徴量探索（kabusys.research.feature_exploration）
      - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
      - pandas 等の外部依存を使わず、標準ライブラリ + DuckDB のみで実装。
    - 再利用ユーティリティを再エクスポート（zscore_normalize 等）。

  - AI / ニュース NLP とレジーム判定（ai）
    - ニュースセンチメント集約（kabusys.ai.news_nlp）
      - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別スコアを取得。
      - バッチサイズ、記事数上限、文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリッピングなどを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
      - API キー注入（api_key 引数）やテスト用に _call_openai_api をパッチ可能にしている。
      - スコア書き込みは部分失敗時にも既存スコアを保持するため、該当コードのみ DELETE → INSERT の方式で冪等的に保存。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321（Nikkei 225 連動）の 200 日 MA 乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で market_regime を評価。
      - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、API失敗時は macro_sentiment=0.0 としてフェイルセーフ動作。
      - DuckDB を用いた冪等性のある DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と、失敗時のロールバック処理。
      - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計。

  - 汎用設計・運用上の配慮
    - ルックアヘッドバイアス回避: 主要処理で datetime.today()/date.today() を参照せず、target_date を明示的に渡す API 設計。
    - OpenAI API 呼び出しに対して明示的なリトライ戦略とログを導入し、API障害をフェイルセーフに扱う。
    - DuckDB のバージョン依存性（executemany の空リスト扱い等）を考慮した実装。
    - テスト容易性のため、OpenAI 呼び出しポイントをパッチ可能にし、api_key を引数で注入可能にしている。

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 環境変数に機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を想定。
  - .env 自動ロード機能を備えるが、OS 環境変数が優先され、.env.local により上書き可能。
  - テストやCI環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑止することを推奨。

Notes / Migration
- 初期リリースのため互換性の過去バージョンは無い。
- DuckDB を使用するため、実行環境に DuckDB と必要なデータテーブル（prices_daily, raw_news, raw_financials, market_calendar, news_symbols, ai_scores, market_regime 等）が存在することを前提とする。
- OpenAI 連携機能を利用する場合は OPENAI_API_KEY を設定する必要あり（api_key 引数での注入も可）。
- calendar_update_job / ETL 処理を実行する場合、J-Quants API 向けの認証情報（JQUANTS_REFRESH_TOKEN 等）や jquants_client 実装が必要。

Acknowledgements
- 本 CHANGELOG はソースコードの docstring／コメント／実装から機能を推測して作成しています。実際のリリースノートやバージョン管理履歴（git commit メッセージ等）が存在する場合は、そちらを正としてください。
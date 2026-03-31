# CHANGELOG

このファイルは Keep a Changelog の形式に従っています。  
全ての変更は SemVer に従ってバージョン管理されています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回公開リリース。本リポジトリに含まれる主要機能と実装上の注意点を記載します。

### 追加（Added）
- パッケージ初期化
  - kabusys パッケージの基本公開 API を追加（__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を定義）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）および環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない読み込みが可能。
  - .env パーサ実装：コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視閾値 / システム設定のプロパティアクセスを実装。必須項目は _require() で明示的にエラー化。
  - KABUSYS_ENV と LOG_LEVEL の値チェック（許容値検証）を実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（銘柄単位）スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に指定時間ウィンドウのニュースを銘柄ごとに集約。
    - OpenAI（gpt-4o-mini）へバッチ送信（複数銘柄を最大 20 件ずつ）。
    - JSON Mode を利用した厳密なレスポンス想定とレスポンスのバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ処理を実装。
    - スコアは ±1 にクリップして ai_scores テーブルへ冪等的に (DELETE → INSERT) 書き込み。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - 補助関数: calc_news_window, _fetch_articles, _score_chunk, _validate_and_extract など。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei-225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次の判定を保存。
    - OpenAI（gpt-4o-mini）呼び出しを内部で行い、API障害時は macro_sentiment を 0.0 にフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ管理（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫した挙動を実装。
    - calendar_update_job: J-Quants から差分でカレンダーを取得・保存する夜間バッチ処理（バックフィル、健全性チェック含む）。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（パイプラインの実行結果集約）。
    - 差分取得・保存・品質チェックの方針を反映した ETL パイプライン用ユーティリティを実装（jquants_client, quality モジュールと連携する設計）。
    - テーブル存在チェックや最大日付取得などのヘルパー関数を実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日移動平均乖離、ATR（20 日）、流動性指標（20 日平均売買代金、出来高比）などを DuckDB 上で計算する関数を実装。
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を標準ライブラリのみで実装。
    - pandas 等の外部依存を避け、DuckDB と組み合わせて使用する設計。

### 変更（Changed）
- 設計上の重要な方針をコードに反映
  - 全ての時刻/日付は明示的に引数で与え、datetime.today() / date.today() を直接参照しない実装（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは各モジュール内で独立して実装し、モジュール間でプライベート関数を共有しないことで結合度を低く保つ設計。
  - DuckDB への書き込みは可能な限り冪等操作（DELETE → INSERT、または ON CONFLICT 相当）で行い、部分失敗時に既存データを不必要に消さない実装。

### 修正（Fixed）
- 耐障害性向上
  - OpenAI API 呼び出しでの 5xx/429/接続エラー/タイムアウトについて適切にリトライし、全リトライ失敗時はフェイルセーフとして処理を進める（スコアを 0.0 とするか対象をスキップ）。
  - JSON レスポンスのパースで余計な前後テキストが混入するケースを考慮して { ... } 抽出のフェールバックを実装。
  - DuckDB executemany の空リストバインドに対する互換性問題を回避するため、空チェックを行ってから executemany を実行。

### セキュリティ（Security）
- 環境変数に依存する API キー（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN など）は Settings 経由で必須チェックを行い、未設定時は明示的にエラーを投げる実装。

### 互換性（Compatibility）
- 本バージョンは DuckDB を想定しており、SQL 文や executemany の挙動は DuckDB のバージョン差に敏感な箇所があるため、DuckDB 0.10 系列との互換性を想定して実装されています。
- OpenAI SDK の例外型（APIError.subclass の status_code など）に配慮した互換性対策を実装。

### 注意事項 / マイグレーションノート（Notes）
- OpenAI API 使用部分は実行時に有効な OPENAI_API_KEY が必要です。テスト時は api_key 引数で注入するか、該当モジュールの _call_openai_api をモックしてください。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後やテスト環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- calendar_update_job は外部 J-Quants クライアント（kabusys.data.jquants_client）に依存します。API 呼び出しの失敗はジョブが 0 を返す形で表現されます。
- ETL / pipeline 部分は jquants_client, quality の実装に依存します。これらの接続・保存ロジックは idempotent 保存を前提としています。

---

（今後のリリースではバグ修正、追加機能、API 互換性の変更をこの CHANGELOG に追記していきます。）
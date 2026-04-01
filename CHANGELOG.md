# CHANGELOG

全ての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。以下の主要機能・設計方針・注意点を含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの公開インターフェースとバージョンを追加（__version__ = 0.1.0）。
  - モジュール群: data, research, ai, execution, strategy, monitoring 等を想定した __all__ を定義。

- 設定・環境変数管理
  - .env ファイルおよび環境変数から設定を読み込む settings モジュールを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索、CWD 非依存）。
  - .env/.env.local の自動ロード（OS 環境変数優先、.env.local は上書き可）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 複雑な .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、行末コメントの扱い等）。
  - 必須鍵取得ヘルパ _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - システム設定（env, log_level）のバリデーションと is_live / is_paper / is_dev プロパティ。
  - DB パス（duckdb, sqlite）や監視閾値などの既定値を設定。

- データプラットフォーム機能（data モジュール）
  - ETL パイプラインの結果を表す ETLResult データクラスの追加（品質チェック情報やエラー一覧を含む）。
  - ETL 用ユーティリティ (pipeline, etl) のインターフェース実装（差分取得、バックフィル設計、品質チェックとの連携設計）。
  - 市場カレンダー管理モジュールを追加（market_calendar テーブル操作、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
  - calendar_update_job：J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存を行う夜間バッチジョブ。

- ニュース NLP / AI モジュール（ai モジュール）
  - news_nlp.score_news: raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ保存する処理を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DB は UTC で比較）。
    - バッチ化（1回あたり最大 20 銘柄）、記事数・文字数トリム、JSON Mode 応答の検証、スコア ±1.0 でクリップ。
    - レート制限やネットワーク断、5xx を対象に指数バックオフによるリトライ。
    - API キー注入可（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - テスト容易性のため _call_openai_api を patch 可能。

  - regime_detector.score_regime: ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロニュースはマクロキーワードでフィルタ、LLM 応答は JSON パース・バリデーション、API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - OpenAI 呼び出しは内部で OpenAI クライアントを生成（api_key 注入可）、リトライロジックあり。
    - レジームはスコア閾値でラベル化し、DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作を行う。

- リサーチ機能（research モジュール）
  - factor_research: モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した実装。データ不足時は None を返す設計。
    - ルックアヘッドバイアス防止のため target_date 以前のデータのみ参照。
  - feature_exploration: 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic：Spearman の ρ）、rank、factor_summary（count/mean/std/min/max/median）など統計解析ユーティリティを追加。
    - 外部依存を持たず標準ライブラリのみで実装。

### 変更 (Changed)
- 初期設計段階の堅牢化
  - DuckDB との互換性考慮（executemany に対する空リスト回避等）。
  - DB 書き込み失敗時のトランザクションロールバック保護と警告ログ出力を徹底。
  - API 呼び出し部分はモジュール間でプライベート関数を共有せず、それぞれ独立実装（テスト容易性・モジュール結合低減）。

### 修正 (Fixed)
- フォールバック挙動の明確化
  - MA など計算に必要な十分なデータがない場合、明示的に中立値（例: ma200_ratio=1.0）を使用して継続するよう設計（WARNING ログ出力）。
  - OpenAI レスポンスのパース失敗や API エラーは例外で全体を止めず、該当部分を 0.0 にフォールバックして処理を継続（フェイルセーフ設計）。

### セキュリティ／運用上の注意 (Security / Ops)
- OpenAI API キー、各種トークン（J-Quants, kabu-station, Slack など）は環境変数で管理。Settings は未設定時に ValueError を放出して明示的に失敗させる箇所があるため、運用時に必ず設定が必要。
- .env 自動ロードはプロジェクトルート探索に依存するため、配布後に自動ロードを期待する場合は .git または pyproject.toml の配置に注意。
- calendar_update_job は最後のカレンダー日付の健全性チェックを行い、極端に将来の日付が検出された場合は処理をスキップする安全策あり。

### 既知の制約 (Known limitations)
- OpenAI を利用する処理は外部 API に依存するため、API コストやレート制限の影響を受ける。429/ネットワーク断/5xx に対してはリトライロジックがあるが、永続障害時は該当日のスコアが得られないことがあり得る。
- PBR や配当利回りなど一部バリューファクターは現バージョンで未実装。
- DuckDB のバージョン差異（リスト型バインド等）に対して互換性を考慮した実装を行っているが、極端に古い/新しいバージョンでは追加調整が必要になる場合がある。

---

このリリースはコードベースから推測した初期機能セットをまとめたものです。将来的なリリースでは、追加ファクター、戦略実行モジュール、モニタリング・アラート機能、テストカバレッジ改善、ドキュメント強化などを予定しています。